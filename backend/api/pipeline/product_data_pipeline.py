import pandas as pd
import numpy as np
import logging
from django.db import models
from typing import List, Dict, Any, Optional
from django.db import transaction, IntegrityError
from api.models.product_features import ProductFeatures, ProductSimilarity
import json
import unicodedata
import re

# Feature extractor'ı import et
from .feature_extractor import ProductFeatureExtractor

# Configure logger
logger = logging.getLogger(__name__)

class ProductDataPipeline:
    """
    Önişlenmiş OpenFoodFacts verilerini ProductFeatures modeline kaydetme pipeline'ı
    """
    
    def __init__(self, batch_size: int = 1000):
        self.batch_size = batch_size
        self.processed_count = 0
        self.error_count = 0
        # Feature extractor'ı başlat
        self.feature_extractor = ProductFeatureExtractor()
    
    def clean_unicode_text(self, text: str) -> str:
        """Unicode problemlerini temizle - geliştirilmiş versiyon"""
        if not text or pd.isna(text):
            return ""
        
        if not isinstance(text, str):
            text = str(text)
        
        try:
            # Önce mevcut encoding'i kontrol et
            if isinstance(text, bytes):
                # Farklı encoding'leri dene
                for encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
                    try:
                        text = text.decode(encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    # Hiçbiri işe yaramazsa errors='ignore' ile decode et
                    text = text.decode('utf-8', errors='ignore')
            
            # Unicode normalizasyonu
            text = unicodedata.normalize('NFKD', text)
            
            # Problemli karakterleri temizle
            text = text.encode('utf-8', errors='ignore').decode('utf-8')
            
            # Kontrolsüz karakterleri temizle
            text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
            
            # Null byte ve diğer problemli karakterleri temizle
            text = text.replace('\x00', '').replace('\ufffd', '')
            
            return text.strip()
            
        except Exception as e:
            logger.warning(f"Unicode temizleme hatası: {e}")
            # Son çare: sadece ASCII karakterleri tut
            return ''.join(char for char in str(text) if ord(char) < 128).strip()
    
    def process_preprocessed_data(self, df_processed: pd.DataFrame) -> Dict[str, Any]:
        """
        Zaten önişlenmiş DataFrame'i alıp feature extraction ve veritabanına kaydet
        """
        logger.info(f"Önişlenmiş veri işleniyor: {len(df_processed)} satır")
        
        try:
            # Unicode temizleme - daha agresif
            df_processed = self._clean_dataframe_unicode(df_processed)
            
            # Null değerleri temizle
            df_processed = self._clean_null_values(df_processed)
            
            # Feature extraction ile işle
            df_with_features = self._apply_feature_extraction(df_processed)
            
            # Veritabanına kaydet
            self._save_to_database(df_with_features)
            
            # Özet rapor
            summary = {
                'total_processed': self.processed_count,
                'total_errors': self.error_count,
                'success_rate': (self.processed_count / (self.processed_count + self.error_count)) * 100 if (self.processed_count + self.error_count) > 0 else 0,
                'final_data_shape': df_with_features.shape
            }
            
            logger.info(f"Pipeline tamamlandı: {summary}")
            return summary
            
        except Exception as e:
            logger.error(f"Pipeline hatası: {str(e)}")
            raise
    
    def process_from_file(self, processed_file_path: str) -> Dict[str, Any]:
        """
        Önişlenmiş CSV/TSV dosyasını okuyup kaydet
        """
        logger.info(f"Önişlenmiş dosya okunuyor: {processed_file_path}")
        
        try:
            # Dosya uzantısına göre okuma
            if processed_file_path.endswith('.csv'):
                df_processed = pd.read_csv(processed_file_path)
            elif processed_file_path.endswith('.tsv'):
                df_processed = pd.read_csv(processed_file_path, sep='\t')
            elif processed_file_path.endswith('.parquet'):
                df_processed = pd.read_parquet(processed_file_path)
            else:
                # Varsayılan olarak CSV dene
                df_processed = pd.read_csv(processed_file_path)
            
            logger.info(f"Dosya okundu: {len(df_processed)} satır")
            
            return self.process_preprocessed_data(df_processed)
            
        except Exception as e:
            logger.error(f"Dosya okuma hatası: {str(e)}")
            raise
    
    def _apply_feature_extraction(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Feature extractor kullanarak özellikleri çıkar
        """
        logger.info("Feature extraction başlatılıyor...")
        
        extracted_features = []
        
        for idx, row in df.iterrows():
            try:
                # Feature extraction
                features = self.feature_extractor.extract_all_features(row)
                
                if features:
                    extracted_features.append(features)
                else:
                    logger.warning(f"Feature extraction başarısız - Index: {idx}")
                    
            except Exception as e:
                logger.error(f"Feature extraction hatası - Index: {idx}: {e}")
                continue
        
        # Feature'ları DataFrame'e çevir
        if extracted_features:
            features_df = pd.DataFrame(extracted_features)
            logger.info(f"Feature extraction tamamlandı: {len(features_df)} ürün")
            return features_df
        else:
            logger.error("Hiç feature çıkarılamadı!")
            return pd.DataFrame()
    
    def _clean_null_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Null değerleri ve problemli veriyi temizle"""
        logger.info("Null değer temizliği başlatılıyor...")
        
        # Object sütunlardaki null byte'ları temizle
        for col in df.select_dtypes(include=['object']).columns:
            try:
                # Null değerleri boş string yap
                df[col] = df[col].fillna('')
                
                # String'e çevir ve null byte'ları temizle
                df[col] = df[col].astype(str).str.replace('\x00', '', regex=False)
                
            except Exception as e:
                logger.warning(f"Null temizleme hatası - {col}: {e}")
                df[col] = ''
        
        return df
    
    def _clean_dataframe_unicode(self, df: pd.DataFrame) -> pd.DataFrame:
        """DataFrame'deki tüm string sütunlarda Unicode temizliği yap - geliştirilmiş"""
        logger.info("Unicode temizliği başlatılıyor...")
        
        # String sütunları belirle
        string_columns = df.select_dtypes(include=['object']).columns
        
        for col in string_columns:
            try:
                logger.debug(f"Sütun temizleniyor: {col}")
                
                # Vectorized temizleme için apply kullan
                df[col] = df[col].apply(self.clean_unicode_text)
                
            except Exception as e:
                logger.warning(f"Sütun {col} Unicode temizliği hatası: {e}")
                # Hatalı sütunu güvenli şekilde temizle
                try:
                    df[col] = df[col].astype(str, errors='ignore')
                    df[col] = df[col].apply(lambda x: ''.join(c for c in str(x) if ord(c) < 128) if x else '')
                except:
                    df[col] = ''
        
        logger.info("Unicode temizliği tamamlandı")
        return df
    
    def _save_to_database(self, df: pd.DataFrame) -> None:
        """
        İşlenmiş verileri ProductFeatures modeline kaydet
        """
        logger.info(f"Veritabanına kaydetme başlıyor: {len(df)} ürün")
        
        # Batch'ler halinde işle
        for i in range(0, len(df), self.batch_size):
            batch_df = df.iloc[i:i + self.batch_size]
            try:
                logger.info(f"Batch {i//self.batch_size + 1} işleniyor...")
                self._save_batch(batch_df)
                logger.info(f"Batch {i//self.batch_size + 1} başarıyla kaydedildi: {len(batch_df)} ürün")
            except Exception as e:
                logger.error(f"Batch {i//self.batch_size + 1} kaydetme hatası: {e}")
                # Tek tek kaydetmeyi dene
                logger.info("Tek tek kaydetme deneniyor...")
                self._save_batch_individually(batch_df)
    
    def _save_batch(self, batch_df: pd.DataFrame) -> None:
        """
        Tek bir batch'i veritabanına kaydet
        """
        product_features_list = []
        
        for idx, row in batch_df.iterrows():
            try:
                # Artık row zaten feature extraction'dan geçmiş
                product_feature = self._create_product_feature_from_extracted(row)
                
                if product_feature:
                    product_features_list.append(product_feature)
                        
            except Exception as e:
                logger.error(f"Ürün işleme hatası - Index: {idx}, Code: {row.get('product_code', 'N/A')}, Hata: {str(e)}")
                self.error_count += 1
                continue
        
        # Bulk create
        if product_features_list:
            try:
                with transaction.atomic():
                    # Batch size'ı küçült ve ignore_conflicts kullan
                    ProductFeatures.objects.bulk_create(
                        product_features_list,
                        ignore_conflicts=True,
                        batch_size=min(100, len(product_features_list))  # Daha küçük batch
                    )
                    self.processed_count += len(product_features_list)
                    
            except Exception as e:
                logger.error(f"Bulk create hatası: {str(e)}")
                # Tek tek kaydetmeyi dene
                logger.warning("Bulk create başarısız, tek tek kaydetme deneniyor...")
                self._save_individually(product_features_list)
    
    def _save_batch_individually(self, batch_df: pd.DataFrame) -> None:
        """
        Batch'teki her ürünü tek tek kaydet
        """
        for idx, row in batch_df.iterrows():
            try:
                product_feature = self._create_product_feature_from_extracted(row)
                if product_feature:
                    # Tek tek kaydet
                    try:
                        product_feature.save()
                        self.processed_count += 1
                    except IntegrityError:
                        # Duplicate key hatası - görmezden gel
                        pass
                    except Exception as save_error:
                        logger.error(f"Tekil kaydetme hatası - Code: {row.get('product_code', 'N/A')}: {save_error}")
                        self.error_count += 1
            except Exception as e:
                logger.error(f"Tekil işleme hatası - Index: {idx}: {e}")
                self.error_count += 1
    
    def _save_individually(self, product_features_list: List[ProductFeatures]) -> None:
        """
        Product features listesini tek tek kaydet
        """
        for product_feature in product_features_list:
            try:
                product_feature.save()
                self.processed_count += 1
            except IntegrityError:
                # Duplicate key - görmezden gel
                pass
            except Exception as e:
                logger.error(f"Tekil kaydetme hatası: {e}")
                self.error_count += 1
    
    def _create_product_feature_from_extracted(self, row: pd.Series) -> Optional[ProductFeatures]:
        """
        Feature extraction'dan gelen veriyi ProductFeatures objesi'ne çevir
        """
        try:
            # JSON alanları için güvenli serileştirme
            def safe_json_parse(value, default=None):
                if default is None:
                    default = {}
                
                if pd.isna(value) or value == '' or value is None:
                    return default
                
                if isinstance(value, (dict, list)):
                    return value
                
                if isinstance(value, str):
                    try:
                        return json.loads(value)
                    except (json.JSONDecodeError, ValueError):
                        return default
                
                return default
            
            # Temel alanları al
            product_code = str(row.get('product_code', ''))[:100]
            if not product_code or product_code == 'unknown':
                logger.warning("Ürün kodu boş veya 'unknown', atlanıyor")
                return None
            
            return ProductFeatures(
                product_code=product_code,
                product_name=str(row.get('product_name', ''))[:500],
                main_category=str(row.get('main_category', 'unknown'))[:200],
                main_brand=str(row.get('main_brand', ''))[:200] if row.get('main_brand') else None,
                main_country=str(row.get('main_country', ''))[:100] if row.get('main_country') else None,
                
                # JSON alanları - feature extractor'dan gelenler zaten dict formatında
                nutrition_vector=row.get('nutrition_vector', {}),
                allergen_vector=row.get('allergen_vector', {}),
                additives_info=row.get('additives_info', {}),
                nutriscore_data=row.get('nutriscore_data', {}),
                health_indicators=row.get('health_indicators', {}),
                macro_ratios=row.get('macro_ratios', {}),
                
                # Sayısal alanlar
                processing_level=int(row.get('processing_level', 1)),
                nutrition_quality_score=float(row.get('nutrition_quality_score', 5.0)),
                health_score=float(row.get('health_score', 0.0)),
                
                # Metin alanları
                ingredients_text=str(row.get('ingredients_text', ''))[:2000],
                ingredients_text_length=int(row.get('ingredients_text_length', 0)),
                ingredients_word_count=int(row.get('ingredients_word_count', 0)),
                
                # Kalite skorları
                data_completeness_score=float(row.get('data_completeness_score', 0.0)),
                is_valid_for_analysis=bool(row.get('is_valid_for_analysis', False))
            )
            
        except KeyError as e:
            logger.error(f"Eksik alan: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"ProductFeatures oluşturma hatası: {str(e)}")
            return None


# Management command için yardımcı fonksiyon
def run_simplified_pipeline(
    processed_data_path: str = None,
    df_processed: pd.DataFrame = None
) -> Dict[str, Any]:
    """
    Basitleştirilmiş pipeline'ı çalıştır
    Args:
        processed_data_path: Önişlenmiş veri dosyasının yolu (CSV/TSV/Parquet)
        df_processed: Zaten yüklenmiş DataFrame (alternatif)
    """
    pipeline = ProductDataPipeline()
    
    if df_processed is not None:
        # DataFrame doğrudan verilmişse
        logger.info("DataFrame kullanılarak pipeline başlatılıyor")
        return pipeline.process_preprocessed_data(df_processed)
    elif processed_data_path:
        # Dosya yolu verilmişse
        logger.info(f"Dosya yolu kullanılarak pipeline başlatılıyor: {processed_data_path}")
        return pipeline.process_from_file(processed_data_path)
    else:
        raise ValueError("processed_data_path veya df_processed parametrelerinden biri gerekli")


# Yardımcı fonksiyon: Full pipeline (preprocessor + feature extraction + database save)
def run_full_pipeline(
    raw_tsv_path: str,
    sample_size: Optional[int] = None,
    save_processed: bool = True,
    processed_output_path: str = None
) -> Dict[str, Any]:
    """
    Ham TSV dosyasından başlayarak tüm pipeline'ı çalıştır
    """
    from aimodels.ml_models.data_preprocessing import OpenFoodFactsPreprocessor
    
    logger.info("Full pipeline başlatılıyor...")
    
    # 1. Preprocessor ile veriyi hazırla
    logger.info("1. Veri önişleme başlatılıyor...")
    preprocessor = OpenFoodFactsPreprocessor()
    
    # Geçici dosya oluşturmadan direkt DataFrame'i al
    df_preprocessed = preprocessor.preprocess(
        file_path=raw_tsv_path,
        output_path=processed_output_path if save_processed else None,
        sample_size=sample_size
    )
    
    # 2. Pipeline ile feature extraction ve kaydetme
    logger.info("2. Feature extraction ve veritabanı kaydı başlatılıyor...")
    pipeline_result = run_simplified_pipeline(df_processed=df_preprocessed)
    
    logger.info("Full pipeline tamamlandı!")
    return pipeline_result


# Veri kalitesi raporu
def generate_data_quality_report() -> Dict[str, Any]:
    """
    Veritabanındaki ürün verilerinin kalite raporunu oluştur
    """
    total_products = ProductFeatures.objects.count()
    valid_products = ProductFeatures.objects.filter(is_valid_for_analysis=True).count()
    
    # Veri tamlık skorları
    completeness_stats = ProductFeatures.objects.aggregate(
        avg_completeness=models.Avg('data_completeness_score'),
        min_completeness=models.Min('data_completeness_score'),
        max_completeness=models.Max('data_completeness_score')
    )
    
    # Kategori dağılımı
    category_distribution = ProductFeatures.objects.values('main_category').annotate(
        count=models.Count('id')
    ).order_by('-count')[:10]
    
    # Sağlık skoru dağılımı
    health_score_stats = ProductFeatures.objects.aggregate(
        avg_health_score=models.Avg('health_score'),
        min_health_score=models.Min('health_score'),
        max_health_score=models.Max('health_score')
    )
    
    return {
        'total_products': total_products,
        'valid_products': valid_products,
        'validity_rate': (valid_products / total_products * 100) if total_products > 0 else 0,
        'completeness_stats': completeness_stats,
        'top_categories': list(category_distribution),
        'health_score_stats': health_score_stats
    }


# Örnek kullanım fonksiyonları
def process_csv_file(csv_path: str) -> Dict[str, Any]:
    """Önceden işlenmiş CSV dosyasını pipeline'a ver"""
    return run_simplified_pipeline(processed_data_path=csv_path)

def process_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    """Önceden işlenmiş DataFrame'i pipeline'a ver"""
    return run_simplified_pipeline(df_processed=df)

def process_raw_tsv(tsv_path: str, sample_size: int = None) -> Dict[str, Any]:
    """Ham TSV dosyasını baştan sona işle"""
    return run_full_pipeline(
        raw_tsv_path=tsv_path,
        sample_size=sample_size,
        save_processed=True
    )