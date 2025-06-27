# management/commands/process_openfoodfacts.py 
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, models
from api.pipeline.product_data_pipeline import (
    run_simplified_pipeline, 
    run_full_pipeline, 
    generate_data_quality_report,
    process_csv_file,
    process_dataframe,
    process_raw_tsv,
    ProductDataPipeline  #  Pipeline sınıfını da import et
)
from api.models.product_features import ProductFeatures, ProductSimilarity
import os
import time
import json

class Command(BaseCommand):
    help = 'OpenFoodFacts verilerini işleyip ProductFeatures modeline kaydet'
    
    def add_arguments(self, parser):
        # Ana dosya parametresi
        parser.add_argument(
            'input_file',
            type=str,
            help='Giriş dosya yolu (TSV/CSV/Parquet)'
        )
        
        # Dosya türü belirtme
        parser.add_argument(
            '--file-type',
            type=str,
            choices=['raw_tsv', 'processed_csv', 'processed_tsv', 'processed_parquet'],
            default='raw_tsv',
            help='Dosya türü (varsayılan: raw_tsv)'
        )
        
        # Temel parametreler
        parser.add_argument(
            '--sample-size',
            type=int,
            default=None,
            help='İşlenecek maksimum satır sayısı (sadece raw_tsv için)'
        )
        
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Batch boyutu (varsayılan: 1000)'
        )
        
        # Veri yönetimi seçenekleri
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            default=False,
            help='Mevcut ProductFeatures verilerini temizle'
        )
        
        parser.add_argument(
            '--save-processed',
            action='store_true',
            default=False,
            help='Önişlenmiş veriyi dosyaya kaydet (sadece raw_tsv için)'
        )
        
        parser.add_argument(
            '--processed-output-path',
            type=str,
            default=None,
            help='Önişlenmiş verinin kaydedileceği yol (save-processed ile birlikte)'
        )
        
        # Sadece rapor
        parser.add_argument(
            '--only-quality-report',
            action='store_true',
            default=False,
            help='Sadece veri kalitesi raporu oluştur (pipeline çalıştırma)'
        )
    
    def handle(self, *args, **options):
        input_file = options['input_file']
        file_type = options['file_type']
        sample_size = options['sample_size']
        batch_size = options['batch_size']  #  Batch size'ı al
        clear_existing = options['clear_existing']
        save_processed = options['save_processed']
        processed_output_path = options['processed_output_path']
        only_quality_report = options['only_quality_report']
        
        # Sadece kalite raporu isteniyor
        if only_quality_report:
            self._generate_and_display_quality_report()
            return

        # Dosya kontrolü
        if not os.path.exists(input_file):
            raise CommandError(f'Dosya bulunamadı: {input_file}')
        
        # Dosya türü doğrulama
        self._validate_file_type(input_file, file_type)
        
        self.stdout.write(f'OpenFoodFacts Pipeline Başlatılıyor...')
        self.stdout.write(f'Giriş Dosyası: {input_file}')
        self.stdout.write(f'Dosya Türü: {file_type}')
        self.stdout.write(f'Batch Boyutu: {batch_size}')
        
        if file_type == 'raw_tsv':
            self.stdout.write(f'Örnek Boyutu: {sample_size or "Tümü"}')
            self.stdout.write(f'Önişlenmiş Veriyi Kaydet: {"Evet" if save_processed else "Hayır"}')
        
        # Mevcut verileri temizle
        if clear_existing:
            self.stdout.write('Mevcut veriler temizleniyor...')
            self._clear_existing_data()
        
        # Pipeline'ı başlat
        start_time = time.time()
        
        try:
            # Dosya türüne göre uygun pipeline'ı çalıştır
            if file_type == 'raw_tsv':
                results = self._process_raw_tsv(
                    input_file, sample_size, save_processed, processed_output_path, batch_size  #  batch_size ekle
                )
            elif file_type in ['processed_csv', 'processed_tsv', 'processed_parquet']:
                results = self._process_preprocessed_file(input_file, batch_size)  #  batch_size ekle
            else:
                raise CommandError(f'Desteklenmeyen dosya türü: {file_type}')
            
            # Sonuçları göster
            self._display_results(results, start_time)
            
            # Kalite raporu oluştur
            if results.get('total_processed', 0) > 0:
                self._generate_and_display_quality_report()
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Pipeline hatası: {str(e)}')
            )
            raise CommandError(f'Pipeline başarısız: {str(e)}')
    
    def _validate_file_type(self, file_path: str, file_type: str):
        """Dosya türü ve uzantı uyumluluğunu kontrol et"""
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_type == 'raw_tsv' and file_extension not in ['.tsv', '.txt']:
            self.stdout.write(
                self.style.WARNING(f'Uyarı: {file_type} için {file_extension} uzantısı beklenmedik')
            )
        elif file_type == 'processed_csv' and file_extension != '.csv':
            self.stdout.write(
                self.style.WARNING(f'Uyarı: {file_type} için {file_extension} uzantısı beklenmedik')
            )
        elif file_type == 'processed_tsv' and file_extension not in ['.tsv', '.txt']:
            self.stdout.write(
                self.style.WARNING(f'Uyarı: {file_type} için {file_extension} uzantısı beklenmedik')
            )
        elif file_type == 'processed_parquet' and file_extension != '.parquet':
            self.stdout.write(
                self.style.WARNING(f'Uyarı: {file_type} için {file_extension} uzantısı beklenmedik')
            )
    
    def _process_raw_tsv(self, tsv_path: str, sample_size: int, save_processed: bool, output_path: str, batch_size: int):
        """Ham TSV dosyasını işle"""
        self.stdout.write('Ham TSV dosyası işleniyor (preprocessing + feature extraction + database save)...')
        
        #  Özel pipeline fonksiyonu - batch_size desteği ile
        return self._run_full_pipeline_with_batch_size(
            raw_tsv_path=tsv_path,
            sample_size=sample_size,
            save_processed=save_processed,
            processed_output_path=output_path,
            batch_size=batch_size
        )
    
    def _process_preprocessed_file(self, file_path: str, batch_size: int):
        """Önişlenmiş dosyayı işle"""
        self.stdout.write('Önişlenmiş dosya işleniyor (feature extraction + database save)...')
        
        #  Pipeline'ı batch_size ile oluştur
        pipeline = ProductDataPipeline(batch_size=batch_size)
        return pipeline.process_from_file(file_path)
    
    def _run_full_pipeline_with_batch_size(self, raw_tsv_path: str, sample_size: int = None, 
                                         save_processed: bool = True, processed_output_path: str = None,
                                         batch_size: int = 1000):
        """Full pipeline'ı batch_size desteği ile çalıştır"""
        from aimodels.ml_models.data_preprocessing import OpenFoodFactsPreprocessor
        
        self.stdout.write("Full pipeline başlatılıyor...")
        
        # 1. Preprocessor ile veriyi hazırla
        self.stdout.write("1. Veri önişleme başlatılıyor...")
        preprocessor = OpenFoodFactsPreprocessor()
        
        # Geçici dosya oluşturmadan direkt DataFrame'i al
        df_preprocessed = preprocessor.preprocess(
            file_path=raw_tsv_path,
            output_path=processed_output_path if save_processed else None,
            sample_size=sample_size
        )
        
        # 2. Pipeline ile feature extraction ve kaydetme - batch_size ile
        self.stdout.write("2. Feature extraction ve veritabanı kaydı başlatılıyor...")
        pipeline = ProductDataPipeline(batch_size=batch_size)  #  batch_size ile oluştur
        pipeline_result = pipeline.process_preprocessed_data(df_preprocessed)
        
        self.stdout.write("Full pipeline tamamlandı!")
        return pipeline_result
    
    def _clear_existing_data(self):
        """Mevcut ProductFeatures ve ProductSimilarity verilerini temizle"""
        try:
            similarity_count = ProductSimilarity.objects.count()
            features_count = ProductFeatures.objects.count()
            
            if similarity_count > 0 or features_count > 0:
                confirm = input(f'Bu işlem {features_count} ProductFeatures ve {similarity_count} ProductSimilarity kaydını silecek. Devam etmek istiyor musunuz? (y/N): ')
                
                if confirm.lower() != 'y':
                    self.stdout.write('İşlem iptal edildi.')
                    return
            
            ProductSimilarity.objects.all().delete()
            ProductFeatures.objects.all().delete()
            
            # Sequence'leri sıfırla (PostgreSQL için)
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT setval(pg_get_serial_sequence('api_productfeatures', 'id'), 1, false);")
                    cursor.execute("SELECT setval(pg_get_serial_sequence('api_productsimilarity', 'id'), 1, false);")
            except Exception:
                pass  # SQLite veya diğer veritabanları için
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Temizlendi: {features_count} ProductFeatures, {similarity_count} ProductSimilarity'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Veri temizleme hatası: {str(e)}')
            )
    
    def _display_results(self, results: dict, start_time: float):
        """Pipeline sonuçlarını göster"""
        duration = time.time() - start_time
        
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS('🎉 OPENFOODFACTS PIPELINE TAMAMLANDI'))
        self.stdout.write('='*70)
        
        # Temel istatistikler
        self.stdout.write(f'⏱️  Toplam Süre: {self._format_duration(duration)}')
        self.stdout.write(f'✅ İşlenen Ürün: {results.get("total_processed", 0):,}')
        self.stdout.write(f'❌ Hatalı Ürün: {results.get("total_errors", 0):,}')
        self.stdout.write(f'📊 Başarı Oranı: %{results.get("success_rate", 0):.2f}')
        
        # Veri şekli bilgisi
        if 'final_data_shape' in results:
            shape = results['final_data_shape']
            self.stdout.write(f'📋 İşlenen Veri: {shape[0]:,} satır × {shape[1]} sütun')
        
        # Database istatistikleri
        self._display_database_stats()
        
        # Performans metrikleri
        total_processed = results.get('total_processed', 0)
        if total_processed > 0 and duration > 0:
            processing_rate = total_processed / duration
            self.stdout.write(f'\n⚡ Performans: {processing_rate:.2f} ürün/saniye')
        
        # JSON formatında da kaydet
        self._save_summary_json(results, duration)
        
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS('Pipeline başarıyla tamamlandı! 🚀'))
    
    def _display_database_stats(self):
        """Veritabanı istatistiklerini göster"""
        self.stdout.write('\n💾 VERİTABANI DURUMU:')
        
        try:
            total_products = ProductFeatures.objects.count()
            valid_products = ProductFeatures.objects.filter(is_valid_for_analysis=True).count()
            similarity_count = ProductSimilarity.objects.count()
            
            self.stdout.write(f'   • Toplam Ürün: {total_products:,}')
            self.stdout.write(f'   • Geçerli Ürün: {valid_products:,}')
            self.stdout.write(f'   • Geçerlilik Oranı: %{(valid_products/total_products*100) if total_products > 0 else 0:.2f}')
            self.stdout.write(f'   • Benzerlik Kayıtları: {similarity_count:,}')
            
            # Ortalama skorlar
            if total_products > 0:
                self._display_average_scores()
                
        except Exception as e:
            self.stdout.write(f'   ❌ Veritabanı istatistikleri alınamadı: {str(e)}')
    
    def _display_average_scores(self):
        """Ortalama skorları göster"""
        try:
            stats = ProductFeatures.objects.aggregate(
                avg_completeness=models.Avg('data_completeness_score'),
                avg_health=models.Avg('health_score'),
                avg_nutrition=models.Avg('nutrition_quality_score'),
                avg_processing=models.Avg('processing_level')
            )
            
            self.stdout.write('\n📊 ORTALAMA SKORLAR:')
            if stats['avg_completeness']:
                self.stdout.write(f'   • Veri Tamlığı: {stats["avg_completeness"]:.3f}')
            if stats['avg_health']:
                self.stdout.write(f'   • Sağlık Skoru: {stats["avg_health"]:.3f}')
            if stats['avg_nutrition']:
                self.stdout.write(f'   • Beslenme Kalitesi: {stats["avg_nutrition"]:.3f}')
            if stats['avg_processing']:
                self.stdout.write(f'   • Ortalama İşleme Seviyesi: {stats["avg_processing"]:.1f}')
                
        except Exception as e:
            self.stdout.write(f'   ❌ Skor istatistikleri alınamadı: {str(e)}')
    
    def _generate_and_display_quality_report(self):
        """Veri kalitesi raporu oluştur ve göster"""
        try:
            self.stdout.write('\n📈 VERİ KALİTESİ RAPORU HAZIRLANYOR...')
            
            quality_report = generate_data_quality_report()
            
            self.stdout.write('\n' + '='*50)
            self.stdout.write(self.style.SUCCESS('📋 VERİ KALİTESİ RAPORU'))
            self.stdout.write('='*50)
            
            # Genel istatistikler
            self.stdout.write(f'📦 Toplam Ürün: {quality_report["total_products"]:,}')
            self.stdout.write(f'✅ Geçerli Ürün: {quality_report["valid_products"]:,}')
            self.stdout.write(f'📊 Geçerlilik Oranı: %{quality_report["validity_rate"]:.2f}')
            
            # Veri tamlık istatistikleri
            completeness = quality_report.get('completeness_stats', {})
            if completeness:
                self.stdout.write('\n📊 VERİ TAMLIK İSTATİSTİKLERİ:')
                if completeness.get('avg_completeness'):
                    self.stdout.write(f'   • Ortalama: {completeness["avg_completeness"]:.3f}')
                if completeness.get('min_completeness') is not None:
                    self.stdout.write(f'   • Minimum: {completeness["min_completeness"]:.3f}')
                if completeness.get('max_completeness'):
                    self.stdout.write(f'   • Maksimum: {completeness["max_completeness"]:.3f}')
            
            # Sağlık skoru istatistikleri
            health_stats = quality_report.get('health_score_stats', {})
            if health_stats:
                self.stdout.write('\n💚 SAĞLIK SKORU İSTATİSTİKLERİ:')
                if health_stats.get('avg_health_score'):
                    self.stdout.write(f'   • Ortalama: {health_stats["avg_health_score"]:.3f}')
                if health_stats.get('min_health_score') is not None:
                    self.stdout.write(f'   • Minimum: {health_stats["min_health_score"]:.3f}')
                if health_stats.get('max_health_score'):
                    self.stdout.write(f'   • Maksimum: {health_stats["max_health_score"]:.3f}')
            
            # Top kategoriler
            top_categories = quality_report.get('top_categories', [])
            if top_categories:
                self.stdout.write('\n🏆 EN POPÜLER KATEGORİLER:')
                for i, category_data in enumerate(top_categories[:8], 1):
                    category = category_data.get('main_category', 'Bilinmeyen')
                    count = category_data.get('count', 0)
                    self.stdout.write(f'   {i:2d}. {category}: {count:,} ürün')
            
            # Raporu JSON olarak kaydet
            self._save_quality_report_json(quality_report)
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Kalite raporu oluşturulamadı: {str(e)}')
            )
    
    def _save_summary_json(self, results: dict, duration: float):
        """Pipeline özetini JSON dosyasına kaydet"""
        try:
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            
            summary_data = {
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'duration_seconds': duration,
                'duration_formatted': self._format_duration(duration),
                'pipeline_results': results,
                'database_stats': {
                    'total_products': ProductFeatures.objects.count(),
                    'valid_products': ProductFeatures.objects.filter(is_valid_for_analysis=True).count(),
                    'total_similarities': ProductSimilarity.objects.count()
                }
            }
            
            # Dosyaya kaydet
            output_file = f'openfoodfacts_pipeline_summary_{timestamp}.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, indent=2, ensure_ascii=False, default=str)
            
            self.stdout.write(f'📄 Pipeline özeti kaydedildi: {output_file}')
            
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'⚠️  Özet dosyası kaydedilemedi: {str(e)}')
            )
    
    def _save_quality_report_json(self, quality_report: dict):
        """Kalite raporunu JSON dosyasına kaydet"""
        try:
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            
            report_data = {
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'quality_report': quality_report
            }
            
            output_file = f'data_quality_report_{timestamp}.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)
            
            self.stdout.write(f'📊 Kalite raporu kaydedildi: {output_file}')
            
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'⚠️  Kalite raporu kaydedilemedi: {str(e)}')
            )
    
    def _format_duration(self, seconds: float) -> str:
        """Süreyi okunabilir formatta göster"""
        if seconds < 60:
            return f'{seconds:.2f} saniye'
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = seconds % 60
            return f'{minutes} dakika {secs:.1f} saniye'
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = seconds % 60
            return f'{hours} saat {minutes} dakika {secs:.1f} saniye'