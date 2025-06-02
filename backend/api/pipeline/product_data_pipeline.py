# backend/pipeline/product_data_pipeline.py

import pandas as pd
import numpy as np
import logging
from django.db import models
from typing import List, Dict, Any, Optional
from django.db import transaction, IntegrityError
from aimodels.ml_models.data_preprocessing import OpenFoodFactsPreprocessor
from .feature_extractor import ProductFeatureExtractor  # Yeni import
from api.models.product_features import ProductFeatures, ProductSimilarity
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
import json

# Configure logger
logger = logging.getLogger(__name__)

class ProductDataPipeline:
    """
    OpenFoodFacts verilerini işleyip ProductFeatures modeline kaydetme pipeline'ı
    """
    
    def __init__(self, batch_size: int = 1000):
        self.batch_size = batch_size
        self.preprocessor = OpenFoodFactsPreprocessor()  # Güncellenen kullanım
        self.feature_extractor = ProductFeatureExtractor()  # Yeni extractor
        self.processed_count = 0
        self.error_count = 0
    
    def process_openfoodfacts_data(self, tsv_file_path: str, max_rows: int = None) -> Dict[str, Any]:
        """
        OpenFoodFacts TSV dosyasını işleyip veritabanına kaydet
        """
        logger.info(f"OpenFoodFacts verisi işleniyor: {tsv_file_path}")
        
        try:
            # Preprocessor ile veriyi işle
            df_processed = self.preprocessor.preprocess(
                file_path=tsv_file_path,
                sample_size=max_rows
            )
            
            logger.info(f"Ön işleme tamamlandı: {len(df_processed)} satır")
            
            # Veritabanına kaydet
            self._save_to_database(df_processed)
            
            # Özet rapor
            summary = {
                'total_processed': self.processed_count,
                'total_errors': self.error_count,
                'success_rate': (self.processed_count / (self.processed_count + self.error_count)) * 100 if (self.processed_count + self.error_count) > 0 else 0,
                'final_data_shape': df_processed.shape
            }
            
            logger.info(f"Pipeline tamamlandı: {summary}")
            return summary
            
        except Exception as e:
            logger.error(f"Pipeline hatası: {str(e)}")
            raise
    
    def _save_to_database(self, df: pd.DataFrame) -> None:
        """
        İşlenmiş verileri ProductFeatures modeline kaydet
        """
        logger.info(f"Veritabanına kaydetme başlıyor: {len(df)} ürün")
        
        # Batch'ler halinde işle
        for i in range(0, len(df), self.batch_size):
            batch_df = df.iloc[i:i + self.batch_size]
            self._save_batch(batch_df)
            logger.info(f"Batch {i//self.batch_size + 1} kaydedildi: {len(batch_df)} ürün")
    
    def _save_batch(self, batch_df: pd.DataFrame) -> None:
        """
        Tek bir batch'i veritabanına kaydet
        """
        product_features_list = []
        
        for _, row in batch_df.iterrows():
            try:
                # Feature extractor kullanarak özellikleri çıkar
                features_dict = self.feature_extractor.extract_all_features(row)
                
                if features_dict:
                    product_feature = self._create_product_feature(features_dict)
                    if product_feature:
                        product_features_list.append(product_feature)
                        
            except Exception as e:
                logger.error(f"Ürün işleme hatası - Code: {row.get('code', 'N/A')}, Hata: {str(e)}")
                self.error_count += 1
        
        # Bulk create
        try:
            with transaction.atomic():
                ProductFeatures.objects.bulk_create(
                    product_features_list,
                    ignore_conflicts=True,
                    batch_size=self.batch_size
                )
                self.processed_count += len(product_features_list)
                
        except Exception as e:
            logger.error(f"Bulk create hatası: {str(e)}")
            self.error_count += len(product_features_list)
    
    def _create_product_feature(self, features_dict: Dict[str, Any]) -> Optional[ProductFeatures]:
        """
        Feature extractor'dan gelen dict'ten ProductFeatures objesi oluştur
        """
        try:
            return ProductFeatures(
                product_code=features_dict['product_code'],
                product_name=features_dict['product_name'],
                main_category=features_dict['main_category'],
                main_brand=features_dict['main_brand'],
                main_country=features_dict['main_country'],
                
                nutrition_vector=features_dict['nutrition_vector'],
                allergen_vector=features_dict['allergen_vector'],
                additives_info=features_dict['additives_info'],
                nutriscore_data=features_dict['nutriscore_data'],
                health_indicators=features_dict['health_indicators'],
                macro_ratios=features_dict['macro_ratios'],
                
                processing_level=features_dict['processing_level'],
                nutrition_quality_score=features_dict['nutrition_quality_score'],
                health_score=features_dict['health_score'],
                
                ingredients_text=features_dict['ingredients_text'],
                ingredients_text_length=features_dict['ingredients_text_length'],
                ingredients_word_count=features_dict['ingredients_word_count'],
                
                data_completeness_score=features_dict['data_completeness_score'],
                is_valid_for_analysis=features_dict['is_valid_for_analysis']
            )
        except KeyError as e:
            logger.error(f"Eksik feature alanı: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"ProductFeatures oluşturma hatası: {str(e)}")
            return None


class ProductSimilarityCalculator:
    """
    Ürün benzerlik skorlarını hesapla ve kaydet
    """
    
    def __init__(self):
        self.scaler = StandardScaler()
    
    def calculate_and_save_similarities(self, batch_size: int = 100, similarity_threshold: float = 0.7):
        """
        Tüm ürünler için benzerlik skorlarını hesapla ve kaydet
        """
        logger.info("Ürün benzerlik hesaplaması başlıyor...")
        
        # Geçerli ürünleri al
        products = ProductFeatures.objects.filter(is_valid_for_analysis=True)
        total_products = products.count()
        
        logger.info(f"Toplam {total_products} ürün için benzerlik hesaplanacak")
        
        if total_products < 2:
            logger.warning("Benzerlik hesaplamak için yeterli ürün yok")
            return
        
        # Batch'ler halinde işle
        for i in range(0, total_products, batch_size):
            batch_products = list(products[i:i + batch_size])
            self._calculate_batch_similarities(batch_products, similarity_threshold)
            logger.info(f"Batch {i//batch_size + 1} tamamlandı")
    
    def _calculate_batch_similarities(self, products: List[ProductFeatures], similarity_threshold: float):
        """Bir batch için benzerlik skorlarını hesapla"""
        
        if len(products) < 2:
            return
            
        # Feature vektörlerini hazırla
        feature_vectors = []
        product_ids = []
        
        for product in products:
            try:
                feature_vector = self._prepare_feature_vector(product)
                if feature_vector:  # Geçerli feature vector varsa
                    feature_vectors.append(feature_vector)
                    product_ids.append(product.id)
            except Exception as e:
                logger.error(f"Feature vector hazırlama hatası (Product ID: {product.id}): {str(e)}")
                continue
        
        if len(feature_vectors) < 2:
            logger.warning("Yeterli geçerli feature vector yok")
            return
        
        try:
            # Vektörleri normalize et
            feature_matrix = np.array(feature_vectors)
            
            # NaN değerlerini kontrol et ve temizle
            feature_matrix = np.nan_to_num(feature_matrix, nan=0.0, posinf=0.0, neginf=0.0)
            
            # Sıfır varyansa sahip sütunları kontrol et
            if feature_matrix.std(axis=0).min() == 0:
                logger.warning("Bazı özellikler sabit değerli, normalizasyon atlanıyor")
                feature_matrix_scaled = feature_matrix
            else:
                feature_matrix_scaled = self.scaler.fit_transform(feature_matrix)
            
            # Cosine similarity hesapla
            similarity_matrix = cosine_similarity(feature_matrix_scaled)
            
            # Benzerlik skorlarını kaydet
            self._save_similarities(product_ids, similarity_matrix, similarity_threshold)
            
        except Exception as e:
            logger.error(f"Benzerlik hesaplama hatası: {str(e)}")
    
    def _save_similarities(self, product_ids: List[int], similarity_matrix: np.ndarray, threshold: float):
        """Benzerlik skorlarını veritabanına kaydet"""
        similarities_to_create = []
        
        for i in range(len(product_ids)):
            for j in range(i + 1, len(product_ids)):
                similarity_score = float(similarity_matrix[i][j])
                
                if similarity_score >= threshold and similarity_score < 1.0:  # Kendisiyle benzerlik 1.0 olur
                    # Kategori benzerliği ve besin benzerliği için ayrı hesaplamalar yapılabilir
                    # Şimdilik hepsini aynı skor olarak kullanıyoruz
                    similarity = ProductSimilarity(
                        product_1_id=product_ids[i],
                        product_2_id=product_ids[j],
                        nutritional_similarity=similarity_score,
                        category_similarity=similarity_score,  # Kategori benzerliği ayrı hesaplanabilir
                        overall_similarity=similarity_score
                    )
                    similarities_to_create.append(similarity)
        
        # Bulk create
        if similarities_to_create:
            try:
                ProductSimilarity.objects.bulk_create(
                    similarities_to_create, 
                    ignore_conflicts=True,
                    batch_size=500
                )
                logger.info(f"{len(similarities_to_create)} benzerlik skoru kaydedildi")
            except Exception as e:
                logger.error(f"Benzerlik skorları kaydetme hatası: {str(e)}")
    
    def _prepare_feature_vector(self, product: ProductFeatures) -> Optional[List[float]]:
        """Ürün için feature vektörü hazırla"""
        try:
            features = []
            
            # Besin değerleri
            nutrition = product.nutrition_vector or {}
            nutrition_features = [
                nutrition.get('energy_kcal_100g', 0),
                nutrition.get('energy_100g', 0),
                nutrition.get('fat_100g', 0),
                nutrition.get('saturated-fat_100g', 0),
                nutrition.get('carbohydrates_100g', 0),
                nutrition.get('sugars_100g', 0),
                nutrition.get('proteins_100g', 0),
                nutrition.get('fiber_100g', 0),
                nutrition.get('salt_100g', 0),
                nutrition.get('sodium_100g', 0)
            ]
            features.extend(nutrition_features)
            
            # Makro oranları
            macro_ratios = product.macro_ratios or {}
            macro_features = [
                macro_ratios.get('fat_ratio', 0),
                macro_ratios.get('carbohydrates_ratio', 0),
                macro_ratios.get('proteins_ratio', 0),
                macro_ratios.get('sugar_carb_ratio', 0)
            ]
            features.extend(macro_features)
            
            # Sağlık göstergeleri
            health = product.health_indicators or {}
            health_features = [
                health.get('high_calorie', 0),
                health.get('high_fat', 0),
                health.get('high_sugar', 0),
                health.get('high_salt', 0),
                health.get('high_protein', 0),
                health.get('high_fiber', 0)
            ]
            features.extend(health_features)
            
            # Alerjen bilgileri
            allergen = product.allergen_vector or {}
            allergen_features = [
                allergen.get('contains_gluten', 0),
                allergen.get('contains_milk', 0),
                allergen.get('contains_eggs', 0),
                allergen.get('contains_soy', 0),
                allergen.get('contains_nuts', 0),
                allergen.get('total_allergens', 0)
            ]
            features.extend(allergen_features)
            
            # Katkı madde bilgileri
            additives = product.additives_info or {}
            additives_features = [
                additives.get('additives_count', 0),
                additives.get('has_risky_additives', 0)
            ]
            features.extend(additives_features)
            
            # Diğer özellikler
            other_features = [
                product.processing_level or 1,
                product.nutrition_quality_score or 5.0,
                product.health_score or 0.0,
                product.data_completeness_score or 0.0
            ]
            features.extend(other_features)
            
            # Tüm değerleri float'a çevir ve NaN kontrolü yap
            features = [float(f) if f is not None else 0.0 for f in features]
            features = [0.0 if np.isnan(f) or np.isinf(f) else f for f in features]
            
            return features
            
        except Exception as e:
            logger.error(f"Feature vector hazırlama hatası: {str(e)}")
            return None


class HealthScoreCalculator:
    """
    Sağlık skorlarını güncellemek için ayrı bir hesaplayıcı
    """
    
    def __init__(self):
        self.feature_extractor = ProductFeatureExtractor()
    
    def recalculate_health_scores(self, batch_size: int = 1000):
        """
        Tüm ürünler için sağlık skorlarını yeniden hesapla
        """
        logger.info("Sağlık skorları yeniden hesaplanıyor...")
        
        products = ProductFeatures.objects.all()
        total_products = products.count()
        
        for i in range(0, total_products, batch_size):
            batch_products = products[i:i + batch_size]
            updated_products = []
            
            for product in batch_products:
                try:
                    # Mock row oluştur (mevcut verilerden)
                    mock_row = self._create_mock_row(product)
                    
                    # Yeni sağlık skoru hesapla
                    new_health_score = self.feature_extractor.calculate_health_score(mock_row)
                    new_nutrition_score = self.feature_extractor.calculate_nutrition_quality_score(mock_row)
                    
                    # Güncelle
                    product.health_score = new_health_score
                    product.nutrition_quality_score = new_nutrition_score
                    updated_products.append(product)
                    
                except Exception as e:
                    logger.error(f"Sağlık skoru hesaplama hatası (Product: {product.product_code}): {str(e)}")
            
            # Bulk update
            if updated_products:
                try:
                    ProductFeatures.objects.bulk_update(
                        updated_products, 
                        ['health_score', 'nutrition_quality_score'],
                        batch_size=batch_size
                    )
                    logger.info(f"Batch {i//batch_size + 1} güncellendi: {len(updated_products)} ürün")
                except Exception as e:
                    logger.error(f"Bulk update hatası: {str(e)}")
    
    def _create_mock_row(self, product: ProductFeatures) -> pd.Series:
        """
        ProductFeatures nesnesinden mock pandas Series oluştur
        """
        data = {}
        
        # Temel bilgiler
        data['code'] = product.product_code
        data['product_name'] = product.product_name
        data['main_category'] = product.main_category
        
        # Besin değerleri
        nutrition = product.nutrition_vector or {}
        for key, value in nutrition.items():
            data[key] = value
        
        # Diğer bilgiler
        data['additives_n'] = (product.additives_info or {}).get('additives_count', 0)
        data['ingredients_text'] = product.ingredients_text or ''
        
        return pd.Series(data)


# Management command için yardımcı fonksiyon
def run_product_pipeline(
    tsv_file_path: str, 
    max_rows: int = None, 
    calculate_similarities: bool = True,
    recalculate_health_scores: bool = False
) -> Dict[str, Any]:
    """
    Pipeline'ı çalıştır (management command'dan kullanılabilir)
    """
    results = {}
    
    # Ana pipeline'ı çalıştır
    pipeline = ProductDataPipeline()
    summary = pipeline.process_openfoodfacts_data(tsv_file_path, max_rows)
    results['pipeline_summary'] = summary
    
    # Sağlık skorlarını yeniden hesapla
    if recalculate_health_scores:
        health_calculator = HealthScoreCalculator()
        health_calculator.recalculate_health_scores()
        results['health_scores_updated'] = True
    
    # Benzerlik hesapla
    if calculate_similarities:
        try:
            calculator = ProductSimilarityCalculator()
            calculator.calculate_and_save_similarities()
            results['similarities_calculated'] = True
        except Exception as e:
            logger.error(f"Benzerlik hesaplama hatası: {str(e)}")
            results['similarities_calculated'] = False
            results['similarity_error'] = str(e)
    
    return results


# Yardımcı fonksiyon: Veri kalitesi raporu
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
        'health_score_stats': health_score_stats,
        'similarity_count': ProductSimilarity.objects.count()
    }