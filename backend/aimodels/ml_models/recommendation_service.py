# aimodels/recommendation_service.py

import os
import logging
import numpy as np
import pandas as pd
from pathlib import Path
import django
from django.conf import settings
import joblib

# Django setup
BASE_DIR = Path(__file__).resolve().parent.parent.parent
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from api.models.product_features import ProductFeatures

logger = logging.getLogger(__name__)

class MLRecommendationService:
    """
    ML Model tabanlı ürün önerisi servisi - Sadece alternatif ürün önerileri için
    """
    _instance = None
    _model_loaded = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._model_loaded:
            self.model = None
            self.scaler = None
            self.feature_columns = []
            self.model_dir = os.path.join(BASE_DIR, 'models')
            self._load_model()
            self.__class__._model_loaded = True

    def _load_model(self):
        """Eğitilmiş modeli yükle"""
        try:
            model_path = os.path.join(self.model_dir, 'personalized_health_model.joblib')
            scaler_path = os.path.join(self.model_dir, 'health_scaler.joblib')
            features_path = os.path.join(self.model_dir, 'health_feature_columns.joblib')

            if all(os.path.exists(path) for path in [model_path, scaler_path, features_path]):
                self.model = joblib.load(model_path)
                self.scaler = joblib.load(scaler_path)
                self.feature_columns = joblib.load(features_path)
                logger.info("ML model başarıyla yüklendi")
            else:
                logger.warning("ML model dosyaları bulunamadı, fallback moduna geçiliyor")
                self.model = None
        except Exception as e:
            logger.error(f"Model yükleme hatası: {str(e)}")
            self.model = None

    def get_personalized_score(self, user_profile, product_data):
        """
        Kullanıcı profili ve ürün verisi için kişiselleştirilmiş skor hesapla
        """
        if self.model is None:
            return self._calculate_fallback_score(user_profile, product_data)

        try:
            # Feature vektörü oluştur (training_model.py ile uyumlu)
            features = self._create_feature_vector(user_profile, product_data)
            
            # DataFrame'e çevir ve eksik kolonları ekle
            features_df = pd.DataFrame([features])
            for col in self.feature_columns:
                if col not in features_df.columns:
                    features_df[col] = 0

            # Sıralamayı düzelt
            features_df = features_df[self.feature_columns]

            # Normalize et ve tahmin yap
            features_scaled = self.scaler.transform(features_df)
            prediction = self.model.predict(features_scaled)

            # Skoru 0-10 arası sınırla
            score = max(0, min(10, prediction[0]))
            return round(score, 2)

        except Exception as e:
            logger.error(f"ML skorlama hatası: {str(e)}")
            return self._calculate_fallback_score(user_profile, product_data)

    def get_product_alternatives(self, user_profile, searched_product, limit=5):
        """
        Aranılan ürüne göre ML tabanlı alternatif öneriler
        """
        try:
            # Aynı kategoride veya benzer kategorilerde ürünleri bul
            category = searched_product.get('main_category', '')
            
            # Daha geniş kategori araması
            similar_products = ProductFeatures.objects.filter(
                main_category__icontains=category.split()[0] if category else '',  # İlk kelimeyi al
                is_valid_for_analysis=True
            ).exclude(product_code=searched_product.get('code', ''))[:100]  # Daha fazla ürün al

            # Eğer yeterli ürün yoksa genel arama yap
            if len(similar_products) < 20:
                similar_products = ProductFeatures.objects.filter(
                    is_valid_for_analysis=True
                ).exclude(product_code=searched_product.get('code', ''))[:100]

            # Her ürün için kişiselleştirilmiş skor hesapla
            scored_products = []
            for product in similar_products:
                try:
                    product_dict = self._convert_product_to_dict(product)
                    personalized_score = self.get_personalized_score(user_profile, product_dict)
                    
                    # Benzerlik bonusu ekle
                    similarity_bonus = self._calculate_similarity_bonus(
                        searched_product, product_dict
                    )
                    
                    final_score = personalized_score + similarity_bonus
                    final_score = max(0, min(10, final_score))
                    
                    scored_products.append({
                        'product': product,
                        'personalized_score': round(final_score, 2),
                        'base_score': personalized_score,
                        'similarity_bonus': similarity_bonus,
                        'recommendation_reason': self._get_recommendation_reason(
                            searched_product, product_dict, final_score
                        )
                    })
                except Exception as e:
                    logger.error(f"Ürün skorlama hatası {product.product_code}: {str(e)}")
                    continue

            # Skora göre sırala ve en iyileri döndür
            scored_products.sort(key=lambda x: x['personalized_score'], reverse=True)
            
            # Çeşitlilik için farklı skorlardaki ürünlerden seç
            diverse_products = self._ensure_diversity(scored_products, limit)
            
            return diverse_products

        except Exception as e:
            logger.error(f"Alternatif ürün önerisi hatası: {str(e)}")
            return []

    def _create_feature_vector(self, user_profile, product_data):
        """
        training_model.py ile tamamen uyumlu feature vektörü oluştur
        """
        features = {}

        # Kullanıcı özellikleri - training_model.py'deki gibi
        features['user_age'] = user_profile.get('age', 30)
        features['user_bmi'] = self._calculate_bmi(user_profile)
        features['user_gender_male'] = 1 if user_profile.get('gender') == 'Male' else 0
        features['user_activity_high'] = 1 if user_profile.get('activity_level') == 'high' else 0
        features['user_activity_moderate'] = 1 if user_profile.get('activity_level') == 'moderate' else 0

        # Sağlık durumu binary features - JSON field'dan liste alınıyor
        medical_conditions = user_profile.get('medical_conditions', [])
        features['has_diabetes'] = 1 if 'diabetes_type_2' in medical_conditions else 0
        features['has_kidney_disease'] = 1 if 'chronic_kidney_disease' in medical_conditions else 0
        features['has_hyperthyroidism'] = 1 if 'hyperthyroidism' in medical_conditions else 0
        features['has_osteoporosis'] = 1 if 'osteoporosis' in medical_conditions else 0

        # Diyet tercihleri - JSON field'dan liste alınıyor
        diet_prefs = user_profile.get('dietary_preferences', [])
        features['prefers_high_protein'] = 1 if 'high_protein' in diet_prefs else 0
        features['prefers_low_fat'] = 1 if 'low_fat' in diet_prefs else 0
        features['is_vegan'] = 1 if 'vegan' in diet_prefs else 0

        # Sağlık hedefleri - JSON field'dan liste alınıyor
        health_goals = user_profile.get('health_goals', [])
        features['goal_muscle_gain'] = 1 if 'muscle_gain' in health_goals else 0
        features['goal_heart_health'] = 1 if 'heart_health' in health_goals else 0
        features['goal_boost_energy'] = 1 if 'boost_energy' in health_goals else 0

        # Ürün özellikleri - training_model.py ile uyumlu
        features['product_energy'] = self._safe_float(product_data.get('energy_kcal', 0))
        features['product_protein'] = self._safe_float(product_data.get('protein', 0))
        features['product_fat'] = self._safe_float(product_data.get('fat', 0))
        features['product_sugar'] = self._safe_float(product_data.get('sugar', 0))
        features['product_salt'] = self._safe_float(product_data.get('salt', 0))
        features['product_fiber'] = self._safe_float(product_data.get('fiber', 0))
        features['product_processing_level'] = product_data.get('processing_level', 3)
        features['product_nutrition_quality'] = product_data.get('nutrition_quality_score', 5)
        features['product_health_score'] = product_data.get('health_score', 5)
        features['product_additives_count'] = product_data.get('additives_count', 0)

        # Binary ürün özellikleri
        features['product_high_sugar'] = product_data.get('is_high_sugar', 0)
        features['product_high_salt'] = product_data.get('is_high_salt', 0)
        features['product_high_fat'] = product_data.get('is_high_fat', 0)
        features['product_high_protein'] = product_data.get('is_high_protein', 0)
        features['product_high_fiber'] = product_data.get('is_high_fiber', 0)
        features['product_has_risky_additives'] = product_data.get('has_risky_additives', 0)

        return features

    def _convert_product_to_dict(self, product_obj):
        """
        ProductFeatures nesnesini training_model.py'deki formatta dict'e çevir
        """
        return {
            'product_code': product_obj.product_code,
            'product_name': product_obj.product_name,
            'main_category': product_obj.main_category,
            'processing_level': product_obj.processing_level,
            'nutrition_quality_score': product_obj.nutrition_quality_score,
            'health_score': product_obj.health_score,
            
            # Besin değerleri
            'energy_kcal': product_obj.get_energy_kcal(),
            'protein': product_obj.get_protein(),
            'fat': product_obj.get_fat(),
            'sugar': product_obj.get_sugar(),
            'salt': product_obj.get_salt(),
            'fiber': product_obj.get_fiber(),
            
            # Binary özellikler
            'is_high_sugar': 1 if product_obj.is_high_sugar() else 0,
            'is_high_salt': 1 if product_obj.is_high_salt() else 0,
            'is_high_fat': 1 if product_obj.is_high_fat() else 0,
            'is_high_protein': 1 if product_obj.is_high_protein() else 0,
            'is_high_fiber': 1 if product_obj.is_high_fiber() else 0,
            'has_risky_additives': 1 if product_obj.has_risky_additives() else 0,
            'additives_count': product_obj.get_additives_count(),
        }

    def _calculate_similarity_bonus(self, searched_product, recommended_product):
        """
        Ürünler arası benzerlik bonusu hesapla
        """
        bonus = 0.0
        
        # Kategori benzerliği
        if searched_product.get('main_category') == recommended_product.get('main_category'):
            bonus += 0.5
        elif self._categories_similar(
            searched_product.get('main_category', ''), 
            recommended_product.get('main_category', '')
        ):
            bonus += 0.3
        
        # Besin değerleri benzerliği
        nutritional_similarity = self._calculate_nutritional_similarity(
            searched_product, recommended_product
        )
        bonus += nutritional_similarity * 0.3
        
        # İşlenmişlik seviyesi benzerliği
        processing_diff = abs(
            searched_product.get('processing_level', 3) - 
            recommended_product.get('processing_level', 3)
        )
        if processing_diff <= 1:
            bonus += 0.2
        
        return min(1.0, bonus)  # Maksimum 1 puan bonus

    def _calculate_nutritional_similarity(self, product1, product2):
        """
        İki ürün arasındaki besin değerleri benzerliği (0-1)
        """
        nutrients = ['energy_kcal', 'protein', 'fat', 'sugar', 'salt', 'fiber']
        similarities = []
        
        for nutrient in nutrients:
            val1 = self._safe_float(product1.get(nutrient, 0))
            val2 = self._safe_float(product2.get(nutrient, 0))
            
            if val1 == 0 and val2 == 0:
                similarities.append(1.0)
            elif val1 == 0 or val2 == 0:
                similarities.append(0.0)
            else:
                # Normalize edilmiş fark hesabı
                max_val = max(val1, val2)
                min_val = min(val1, val2)
                similarity = min_val / max_val if max_val > 0 else 1.0
                similarities.append(similarity)
        
        return np.mean(similarities)

    def _categories_similar(self, cat1, cat2):
        """
        İki kategori benzer mi kontrol et
        """
        if not cat1 or not cat2:
            return False
        
        cat1_words = set(cat1.lower().split())
        cat2_words = set(cat2.lower().split())
        
        # Ortak kelime oranı
        intersection = len(cat1_words.intersection(cat2_words))
        union = len(cat1_words.union(cat2_words))
        
        similarity = intersection / union if union > 0 else 0
        return similarity > 0.3

    def _ensure_diversity(self, scored_products, limit):
        """
        Önerilerde çeşitlilik sağla - farklı kategorilerden ürünler seç
        """
        if len(scored_products) <= limit:
            return scored_products
        
        diverse_products = []
        seen_categories = set()
        
        # İlk olarak en yüksek skoru al
        diverse_products.append(scored_products[0])
        seen_categories.add(scored_products[0]['product'].main_category)
        
        # Farklı kategorilerden ürünler ekle
        for product in scored_products[1:]:
            if len(diverse_products) >= limit:
                break
                
            category = product['product'].main_category
            if category not in seen_categories or len(diverse_products) < limit // 2:
                diverse_products.append(product)
                seen_categories.add(category)
        
        # Eksik varsa en yüksek skorlu ürünlerle tamamla
        if len(diverse_products) < limit:
            for product in scored_products:
                if len(diverse_products) >= limit:
                    break
                if product not in diverse_products:
                    diverse_products.append(product)
        
        return diverse_products[:limit]

    def _get_recommendation_reason(self, searched_product, recommended_product, score):
        """
        Öneri sebebini belirle - daha detaylı
        """
        reasons = []
        
        # Skor bazlı açıklama
        if score >= 8.5:
            reasons.append("Sizin için mükemmel uyum")
        elif score >= 7.0:
            reasons.append("Sizin için çok uygun")
        elif score >= 6.0:
            reasons.append("Sizin için iyi seçim")
        else:
            reasons.append("Alternatif seçenek")
        
        # Kategori benzerliği
        if searched_product.get('main_category') == recommended_product.get('main_category'):
            reasons.append("Aynı kategori")
        
        # Besin değerleri karşılaştırması
        if recommended_product.get('protein', 0) > searched_product.get('protein', 0):
            reasons.append("Daha yüksek protein")
        
        if recommended_product.get('fiber', 0) > searched_product.get('fiber', 0):
            reasons.append("Daha yüksek fiber")
        
        if recommended_product.get('sugar', 0) < searched_product.get('sugar', 0):
            reasons.append("Daha az şeker")
        
        if recommended_product.get('salt', 0) < searched_product.get('salt', 0):
            reasons.append("Daha az tuz")
        
        # İşlenmişlik karşılaştırması
        searched_processing = searched_product.get('processing_level', 3)
        recommended_processing = recommended_product.get('processing_level', 3)
        if recommended_processing < searched_processing:
            reasons.append("Daha az işlenmiş")
        
        # Nutriscore karşılaştırması
        searched_quality = searched_product.get('nutrition_quality_score', 5)
        recommended_quality = recommended_product.get('nutrition_quality_score', 5)
        if recommended_quality > searched_quality:
            reasons.append("Daha iyi beslenme skoru")
        
        return " • ".join(reasons[:3]) if reasons else "ML tabanlı öneri"  # Maksimum 3 sebep

    def _calculate_fallback_score(self, user_profile, product_data):
        """
        Model yoksa kullanılacak geliştirilmiş kural tabanlı skor
        """
        base_score = 5.0

        # Temel ürün kalitesi
        nutrition_quality = product_data.get('nutrition_quality_score', 5)
        base_score += (nutrition_quality - 5) * 0.4

        # İşlenmişlik cezası
        processing_level = product_data.get('processing_level', 3)
        base_score -= (processing_level - 1) * 0.5

        # Kullanıcı yaşına göre ayarlama
        age = user_profile.get('age', 30)
        if age > 65:
            # Yaşlılar için düşük tuz ve yüksek fiber bonusu
            if product_data.get('salt', 0) < 0.5:
                base_score += 0.5
            if product_data.get('fiber', 0) > 5:
                base_score += 0.5
        elif age < 25:
            # Gençler için protein bonusu
            if product_data.get('protein', 0) > 15:
                base_score += 0.3

        # BMI'ya göre ayarlama
        bmi = self._calculate_bmi(user_profile)
        if bmi > 30:  # Obez
            if product_data.get('energy_kcal', 0) < 200:
                base_score += 0.8
            if not product_data.get('is_high_sugar', 0):
                base_score += 0.5
        elif bmi < 18.5:  # Zayıf
            if product_data.get('energy_kcal', 0) > 300:
                base_score += 0.6

        # Sağlık durumlarına göre ayarlama
        medical_conditions = user_profile.get('medical_conditions', [])
        for condition in medical_conditions:
            if condition == 'diabetes_type_2':
                if product_data.get('sugar', 0) < 5:
                    base_score += 1.0
                elif product_data.get('sugar', 0) > 15:
                    base_score -= 2.0
            elif condition == 'hyperthyroidism':
                if product_data.get('salt', 0) < 0.5:
                    base_score += 0.5
                elif product_data.get('is_high_salt', 0):
                    base_score -= 1.5

        return max(0, min(10, base_score))

    def _calculate_bmi(self, user_profile):
        """BMI hesapla - user_profile'dan direkt al ya da hesapla"""
        # Direkt BMI varsa kullan
        if user_profile.get('bmi'):
            return user_profile['bmi']
        
        # Yoksa hesapla
        height = user_profile.get('height', 170)  # cm
        weight = user_profile.get('weight', 70)   # kg
        
        if height and weight and height > 0:
            return round(weight / ((height/100) ** 2), 1)
        
        # Varsayılan değer
        age = user_profile.get('age', 30)
        if age < 25:
            return 22
        elif age > 50:
            return 26
        return 24

    def _safe_float(self, value):
        """Güvenli float dönüşümü"""
        try:
            return float(value) if value is not None else 0.0
        except (ValueError, TypeError):
            return 0.0


# Singleton instance
ml_recommendation_service = MLRecommendationService()