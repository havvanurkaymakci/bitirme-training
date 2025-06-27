# aimodels/ml_models/ml_product_score.py

import os
import logging
import pandas as pd
from pathlib import Path
import django
import joblib
from typing import Dict, List, Optional, Any

# Django setup
BASE_DIR = Path(__file__).resolve().parent.parent.parent
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from api.models.product_features import ProductFeatures

logger = logging.getLogger(__name__)

class MLProductScoreService:
    """
    ML Model tabanlı kişiselleştirilmiş ürün skoru hesaplama servisi
    """
    def __init__(self):
        self.model = None
        self.scaler = None  
        self.feature_columns = []
        self.model_dir = os.path.join(BASE_DIR, 'models')
        self._load_model()

    def _load_model(self):
        """ML modelini yükle"""
        try:
            model_path = os.path.join(self.model_dir, 'personalized_health_model.joblib')
            scaler_path = os.path.join(self.model_dir, 'health_scaler.joblib') 
            features_path = os.path.join(self.model_dir, 'health_feature_columns.joblib')

            if all(os.path.exists(path) for path in [model_path, scaler_path, features_path]):
                self.model = joblib.load(model_path)
                self.scaler = joblib.load(scaler_path)
                self.feature_columns = joblib.load(features_path)
                logger.info("✅ ML score model yüklendi")
            else:
                logger.warning("⚠️ ML model dosyaları bulunamadı")
                
        except Exception as e:
            logger.error(f"❌ Model yükleme hatası: {e}")

    def get_personalized_score(self, user_profile: Dict[str, Any], product_code: str) -> Optional[Dict[str, Any]]:
        """
        Kullanıcı profili ve ürün için kişiselleştirilmiş skor hesapla (0-10)
        
        Args:
            user_profile: Kullanıcı profil verisi
            product_code: Ürün kodu
            
        Returns:
            Dict: Skor ve analiz bilgileri veya None
        """
        try:
            # Ürünü bul
            product = ProductFeatures.objects.get(product_code=product_code)
            
            # ML ile skor hesapla
            ml_score = self._calculate_ml_score(user_profile, product)
            
            # Detaylı analiz
            analysis = self._get_score_analysis(user_profile, product, ml_score)
            
            return {
                'personalized_score': round(ml_score, 2),
                'score_level': self._get_score_level(ml_score),
                'analysis': analysis,
                'product_info': {
                    'name': product.product_name,
                    'category': product.main_category,
                    'health_score': product.health_score,
                    'nutrition_quality': product.nutrition_quality_score,
                    'product_code': product_code
                }
            }
            
        except ProductFeatures.DoesNotExist:
            logger.error(f"Ürün bulunamadı: {product_code}")
            return None
        except Exception as e:
            logger.error(f"Skor hesaplama hatası: {e}")
            return None

    def calculate_bulk_scores(self, user_profile: Dict[str, Any], product_codes: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Birden fazla ürün için toplu skor hesaplama
        
        Args:
            user_profile: Kullanıcı profil verisi
            product_codes: Ürün kodları listesi
            
        Returns:
            Dict: Her ürün kodu için skor bilgileri
        """
        results = {}
        
        for product_code in product_codes:
            try:
                result = self.get_personalized_score(user_profile, product_code)
                results[product_code] = result
            except Exception as e:
                logger.error(f"Bulk skor hesaplama hatası ({product_code}): {e}")
                results[product_code] = None
                
        return results

    def _calculate_ml_score(self, user_profile: Dict[str, Any], product: ProductFeatures) -> float:
        """ML model ile kişiselleştirilmiş skor hesapla"""
        if self.model is None:
            return self._fallback_score(user_profile, product)
        
        try:
            # Feature vektörü oluştur
            features = self._create_feature_vector(user_profile, product)
            
            # DataFrame'e çevir ve eksik kolonları ekle
            df = pd.DataFrame([features])
            for col in self.feature_columns:
                if col not in df.columns:
                    df[col] = 0
            df = df[self.feature_columns]
            
            # Normalize et ve tahmin yap
            features_scaled = self.scaler.transform(df)
            prediction = self.model.predict(features_scaled)[0]
            
            return max(0, min(10, prediction))
            
        except Exception as e:
            logger.error(f"ML skorlama hatası: {e}")
            return self._fallback_score(user_profile, product)

    def _create_feature_vector(self, user_profile: Dict[str, Any], product: ProductFeatures) -> Dict[str, float]:
        """Training model ile uyumlu feature vektörü oluştur"""
        features = {}
        
        # Kullanıcı özellikleri
        features['user_age'] = user_profile.get('age', 30)
        features['user_bmi'] = self._calculate_bmi(user_profile)
        features['user_gender_male'] = 1 if user_profile.get('gender') == 'Male' else 0
        features['user_activity_high'] = 1 if user_profile.get('activity_level') == 'high' else 0
        features['user_activity_moderate'] = 1 if user_profile.get('activity_level') == 'moderate' else 0
        
        # Sağlık durumu
        conditions = user_profile.get('medical_conditions', [])
        features['has_diabetes'] = 1 if 'diabetes_type_2' in conditions else 0
        features['has_kidney_disease'] = 1 if 'chronic_kidney_disease' in conditions else 0
        features['has_hyperthyroidism'] = 1 if 'hyperthyroidism' in conditions else 0
        features['has_osteoporosis'] = 1 if 'osteoporosis' in conditions else 0
        
        # Diyet tercihleri
        diet_prefs = user_profile.get('dietary_preferences', [])
        features['prefers_high_protein'] = 1 if 'high_protein' in diet_prefs else 0
        features['prefers_low_fat'] = 1 if 'low_fat' in diet_prefs else 0
        features['is_vegan'] = 1 if 'vegan' in diet_prefs else 0
        
        # Sağlık hedefleri
        goals = user_profile.get('health_goals', [])
        features['goal_muscle_gain'] = 1 if 'muscle_gain' in goals else 0
        features['goal_heart_health'] = 1 if 'heart_health' in goals else 0
        features['goal_boost_energy'] = 1 if 'boost_energy' in goals else 0
        
        # Ürün özellikleri - safe getter metotları kullan
        features['product_energy'] = self._safe_get_nutrient(product, 'get_energy_kcal')
        features['product_protein'] = self._safe_get_nutrient(product, 'get_protein')
        features['product_fat'] = self._safe_get_nutrient(product, 'get_fat')
        features['product_sugar'] = self._safe_get_nutrient(product, 'get_sugar')
        features['product_salt'] = self._safe_get_nutrient(product, 'get_salt')
        features['product_fiber'] = self._safe_get_nutrient(product, 'get_fiber')
        features['product_processing_level'] = getattr(product, 'processing_level', 2)
        features['product_nutrition_quality'] = getattr(product, 'nutrition_quality_score', 5.0)
        features['product_health_score'] = getattr(product, 'health_score', 5.0)
        features['product_additives_count'] = self._safe_get_nutrient(product, 'get_additives_count')
        
        # Binary ürün özellikleri - safe checker metotları kullan
        features['product_high_sugar'] = 1 if self._safe_check_property(product, 'is_high_sugar') else 0
        features['product_high_salt'] = 1 if self._safe_check_property(product, 'is_high_salt') else 0
        features['product_high_fat'] = 1 if self._safe_check_property(product, 'is_high_fat') else 0
        features['product_high_protein'] = 1 if self._safe_check_property(product, 'is_high_protein') else 0
        features['product_high_fiber'] = 1 if self._safe_check_property(product, 'is_high_fiber') else 0
        features['product_has_risky_additives'] = 1 if self._safe_check_property(product, 'has_risky_additives') else 0
        
        return features

    def _safe_get_nutrient(self, product: ProductFeatures, method_name: str) -> float:
        """Güvenli besin değeri alma"""
        try:
            if hasattr(product, method_name):
                method = getattr(product, method_name)
                return float(method() or 0)
            return 0.0
        except (AttributeError, TypeError, ValueError):
            return 0.0

    def _safe_check_property(self, product: ProductFeatures, method_name: str) -> bool:
        """Güvenli özellik kontrolü"""
        try:
            if hasattr(product, method_name):
                method = getattr(product, method_name)
                return bool(method())
            return False
        except (AttributeError, TypeError):
            return False

    def _get_score_analysis(self, user_profile: Dict[str, Any], product: ProductFeatures, score: float) -> Dict[str, List[str]]:
        """Skor analizi ve açıklaması"""
        analysis = {
            'positive_points': [],
            'negative_points': [],
            'recommendations': []
        }
        
        # Pozitif noktalar
        health_score = getattr(product, 'health_score', 5.0)
        if health_score >= 7:
            analysis['positive_points'].append("Yüksek sağlık skoru")
        
        protein = self._safe_get_nutrient(product, 'get_protein')
        if protein > 15:
            analysis['positive_points'].append("Yüksek protein içeriği")
            
        fiber = self._safe_get_nutrient(product, 'get_fiber')
        if fiber > 5:
            analysis['positive_points'].append("İyi fiber kaynağı")
            
        processing_level = getattr(product, 'processing_level', 3)
        if processing_level <= 2:
            analysis['positive_points'].append("Düşük işlenmişlik seviyesi")
        
        # Negatif noktalar
        if self._safe_check_property(product, 'is_high_sugar'):
            analysis['negative_points'].append("Yüksek şeker içeriği")
            
        if self._safe_check_property(product, 'is_high_salt'):
            analysis['negative_points'].append("Yüksek tuz içeriği")
            
        if self._safe_check_property(product, 'has_risky_additives'):
            analysis['negative_points'].append("Riskli katkı maddeleri içeriyor")
        
        # Kişiselleştirilmiş öneriler
        conditions = user_profile.get('medical_conditions', [])
        if 'diabetes_type_2' in conditions:
            sugar = self._safe_get_nutrient(product, 'get_sugar')
            if sugar > 10:
                analysis['recommendations'].append("Diyabet nedeniyle şeker oranına dikkat edin")
            else:
                analysis['recommendations'].append("Diyabet yönetimi için uygun seçim")
        
        bmi = self._calculate_bmi(user_profile)
        if bmi > 30:
            energy = self._safe_get_nutrient(product, 'get_energy_kcal')
            if energy < 200:
                analysis['recommendations'].append("Kilo kontrolü için uygun kalori miktarı")
            else:
                analysis['recommendations'].append("Kalori kontrolü yaparak tüketin")
        
        goals = user_profile.get('health_goals', [])
        if 'muscle_gain' in goals and protein > 15:
            analysis['recommendations'].append("Kas gelişimi hedefi için ideal protein kaynağı")
        
        return analysis

    def _get_score_level(self, score: float) -> Dict[str, str]:
        """Skor seviyesini belirle"""
        if score >= 8.5:
            return {"level": "Mükemmel", "color": "green", "description": "Size çok uygun"}
        elif score >= 7.0:
            return {"level": "İyi", "color": "lightgreen", "description": "Sizin için iyi seçim"}
        elif score >= 5.5:
            return {"level": "Orta", "color": "orange", "description": "Dikkatli tüketin"}
        elif score >= 4.0:
            return {"level": "Zayıf", "color": "red", "description": "Size pek uygun değil"}
        else:
            return {"level": "Kötü", "color": "darkred", "description": "Önerilmez"}

    def _fallback_score(self, user_profile: Dict[str, Any], product: ProductFeatures) -> float:
        """Model yoksa basit kural tabanlı skor"""
        score = 5.0
        
        # Temel ürün kalitesi
        nutrition_quality = getattr(product, 'nutrition_quality_score', 5.0)
        processing_level = getattr(product, 'processing_level', 2)
        
        score += (nutrition_quality - 5) * 0.4
        score -= (processing_level - 1) * 0.5
        
        # BMI uyumu
        bmi = self._calculate_bmi(user_profile)
        energy = self._safe_get_nutrient(product, 'get_energy_kcal')
        
        if bmi > 30 and energy < 200:
            score += 1.5
        elif bmi < 18.5 and energy > 300:
            score += 1.0
        
        # Sağlık durumu uyumu
        conditions = user_profile.get('medical_conditions', [])
        if 'diabetes_type_2' in conditions:
            sugar = self._safe_get_nutrient(product, 'get_sugar')
            if sugar < 5:
                score += 2.0
            elif sugar > 15:
                score -= 3.0
        
        return max(0, min(10, score))

    def _calculate_bmi(self, user_profile: Dict[str, Any]) -> float:
        """BMI hesapla"""
        if user_profile.get('bmi'):
            return float(user_profile['bmi'])
        
        height = user_profile.get('height', 170)
        weight = user_profile.get('weight', 70)
        
        if height and weight:
            return weight / ((height/100) ** 2)
        
        return 24.0  # Varsayılan BMI

    def get_score_comparison(self, user_profile: Dict[str, Any], product_codes: List[str]) -> Dict[str, Any]:
        """
        Birden fazla ürün için skor karşılaştırması
        
        Args:
            user_profile: Kullanıcı profil verisi
            product_codes: Karşılaştırılacak ürün kodları
            
        Returns:
            Dict: Karşılaştırma sonuçları
        """
        scores = self.calculate_bulk_scores(user_profile, product_codes)
        
        valid_scores = {k: v for k, v in scores.items() if v is not None}
        
        if not valid_scores:
            return {'error': 'Hiçbir ürün için skor hesaplanamadı'}
        
        # En iyi ve en kötü ürünleri bul
        best_product = max(valid_scores.items(), key=lambda x: x[1]['personalized_score'])
        worst_product = min(valid_scores.items(), key=lambda x: x[1]['personalized_score'])
        
        return {
            'scores': valid_scores,
            'best_product': {
                'product_code': best_product[0],
                'score': best_product[1]['personalized_score'],
                'name': best_product[1]['product_info']['name']
            },
            'worst_product': {
                'product_code': worst_product[0],
                'score': worst_product[1]['personalized_score'],
                'name': worst_product[1]['product_info']['name']
            },
            'average_score': sum(v['personalized_score'] for v in valid_scores.values()) / len(valid_scores)
        }

# Singleton instance
ml_product_score_service = MLProductScoreService()