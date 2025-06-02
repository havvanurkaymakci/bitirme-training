# management/commands/process_openfoodfacts.py

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, models
from api.pipeline.product_data_pipeline import run_product_pipeline, generate_data_quality_report
from api.models.product_features import ProductFeatures, ProductSimilarity
import os
import time
import json

class Command(BaseCommand):
    help = 'OpenFoodFacts TSV verilerini işleyip ProductFeatures modeline kaydet'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'tsv_file',
            type=str,
            help='OpenFoodFacts TSV dosya yolu'
        )
        parser.add_argument(
            '--max-rows',
            type=int,
            default=None,
            help='İşlenecek maksimum satır sayısı (test için)'
        )
        parser.add_argument(
            '--no-similarities',
            action='store_true',
            default=False,
            help='Benzerlik hesaplamalarını atla'
        )
        parser.add_argument(
            '--recalculate-health-scores',
            action='store_true',
            default=False,
            help='Sağlık skorlarını yeniden hesapla'
        )
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            default=False,
            help='Mevcut ProductFeatures verilerini temizle'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Batch boyutu (varsayılan: 1000)'
        )
        parser.add_argument(
            '--similarity-threshold',
            type=float,
            default=0.7,
            help='Benzerlik threshold değeri (varsayılan: 0.7)'
        )
        parser.add_argument(
            '--only-quality-report',
            action='store_true',
            default=False,
            help='Sadece veri kalitesi raporu oluştur (pipeline çalıştırma)'
        )
    
    def handle(self, *args, **options):
        tsv_file = options['tsv_file']
        max_rows = options['max_rows']
        calculate_similarities = not options['no_similarities']
        recalculate_health_scores = options['recalculate_health_scores']
        clear_existing = options['clear_existing']
        batch_size = options['batch_size']
        similarity_threshold = options['similarity_threshold']
        only_quality_report = options['only_quality_report']
        
        # Sadece kalite raporu isteniyor
        if only_quality_report:
            self._generate_and_display_quality_report()
            return

        # Dosya kontrolü
        if not os.path.exists(tsv_file):
            raise CommandError(f'TSV dosyası bulunamadı: {tsv_file}')
        
        # Dosya uzantısı kontrolü
        if not tsv_file.lower().endswith(('.tsv', '.txt')):
            self.stdout.write(
                self.style.WARNING(f'Dosya TSV formatında değil gibi görünüyor: {tsv_file}')
            )
        
        self.stdout.write(f'OpenFoodFacts Pipeline Başlatılıyor...')
        self.stdout.write(f'TSV Dosyası: {tsv_file}')
        self.stdout.write(f'Maksimum Satır: {max_rows or "Tümü"}')
        self.stdout.write(f'Batch Boyutu: {batch_size}')
        self.stdout.write(f'Benzerlik Hesapla: {"Evet" if calculate_similarities else "Hayır"}')
        self.stdout.write(f'Sağlık Skorları Yeniden Hesapla: {"Evet" if recalculate_health_scores else "Hayır"}')
        
        if calculate_similarities:
            self.stdout.write(f'Benzerlik Threshold: {similarity_threshold}')
        
        # Mevcut verileri temizle
        if clear_existing:
            self.stdout.write('Mevcut veriler temizleniyor...')
            self._clear_existing_data()
        
        # Pipeline'ı başlat
        start_time = time.time()
        
        try:
            # Pipeline parametrelerini ayarla
            pipeline_params = {
                'tsv_file_path': tsv_file,  # TSV dosyası için doğru parametre adı
                'max_rows': max_rows,
                'calculate_similarities': calculate_similarities,
                'recalculate_health_scores': recalculate_health_scores
            }
            
            # Pipeline'ı çalıştır
            results = run_product_pipeline(**pipeline_params)
            
            # Sonuçları göster
            self._display_results(results, start_time, similarity_threshold)
            
            # Kalite raporu oluştur
            if results.get('pipeline_summary', {}).get('total_processed', 0) > 0:
                self._generate_and_display_quality_report()
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Pipeline hatası: {str(e)}')
            )
            raise CommandError(f'Pipeline başarısız: {str(e)}')
    
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
    
    def _display_results(self, results: dict, start_time: float, similarity_threshold: float):
        """Pipeline sonuçlarını göster"""
        duration = time.time() - start_time
        pipeline_summary = results.get('pipeline_summary', {})
        
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS('🎉 OPENFOODFACTS PIPELINE TAMAMLANDI'))
        self.stdout.write('='*70)
        
        # Temel istatistikler
        self.stdout.write(f'⏱️  Toplam Süre: {self._format_duration(duration)}')
        self.stdout.write(f'✅ İşlenen Ürün: {pipeline_summary.get("total_processed", 0):,}')
        self.stdout.write(f'❌ Hatalı Ürün: {pipeline_summary.get("total_errors", 0):,}')
        self.stdout.write(f'📊 Başarı Oranı: %{pipeline_summary.get("success_rate", 0):.2f}')
        
        # Veri şekli bilgisi
        if 'final_data_shape' in pipeline_summary:
            shape = pipeline_summary['final_data_shape']
            self.stdout.write(f'📋 İşlenen Veri: {shape[0]:,} satır × {shape[1]} sütun')
        
        # Sağlık skorları güncellemesi
        if results.get('health_scores_updated'):
            self.stdout.write(f'💚 Sağlık skorları güncellendi')
        
        # Benzerlik hesaplaması
        if results.get('similarities_calculated'):
            similarity_count = ProductSimilarity.objects.count()
            self.stdout.write(f'🔗 Hesaplanan Benzerlik: {similarity_count:,} (threshold: {similarity_threshold})')
        elif 'similarity_error' in results:
            self.stdout.write(f'⚠️  Benzerlik hesaplama hatası: {results["similarity_error"]}')
        
        # Database istatistikleri
        self._display_database_stats()
        
        # Performans metrikleri
        total_processed = pipeline_summary.get('total_processed', 0)
        if total_processed > 0:
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
            self.stdout.write(f'🔗 Benzerlik Sayısı: {quality_report["similarity_count"]:,}')
            
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