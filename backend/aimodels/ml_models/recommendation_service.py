# aimodels/ml_models/recommendation_service.py

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
    ML Model tabanlı ürün önerisi servisi
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

    def get_product_alternatives(self, user_profile, product_code, limit=6, min_score_threshold=6.0):
        """
        VIEW'e uyumlu alternatif ürün önerisi
        """
        try:
            # Hedef ürünü bul
            try:
                target_product = ProductFeatures.objects.get(
                    product_code=product_code,
                    is_valid_for_analysis=True
                )
            except ProductFeatures.DoesNotExist:
                return None

            target_product_dict = self._convert_product_to_dict(target_product)
            
            # Benzer ürünleri bul
            category = target_product.main_category
            similar_products = ProductFeatures.objects.filter(
                main_category__icontains=category.split()[0] if category else '',
                is_valid_for_analysis=True
            ).exclude(product_code=product_code)[:100]

            if len(similar_products) < 20:
                similar_products = ProductFeatures.objects.filter(
                    is_valid_for_analysis=True
                ).exclude(product_code=product_code)[:100]

            # Skorlama ve filtreleme
            alternatives = []
            for product in similar_products:
                try:
                    product_dict = self._convert_product_to_dict(product)
                    
                    # ML skoru
                    ml_score = self.get_personalized_score(user_profile, product_dict)
                    target_score = self.get_personalized_score(user_profile, target_product_dict)
                    
                    # Bonuslar
                    similarity_bonus = self._calculate_similarity_bonus(target_product_dict, product_dict)
                    improvement_bonus = max(0, ml_score - target_score) * 0.5
                    
                    # Final skor
                    final_score = ml_score + similarity_bonus + improvement_bonus
                    final_score = max(0, min(10, final_score))
                    
                    if final_score >= min_score_threshold:
                        alternatives.append({
                            'product': product,
                            'final_score': round(final_score, 2),
                            'ml_score': round(ml_score, 2),
                            'target_score': round(target_score, 2),
                            'score_improvement': round(ml_score - target_score, 2),
                            'similarity_bonus': round(similarity_bonus, 2),
                            'improvement_bonus': round(improvement_bonus, 2),
                            'reason': self._get_recommendation_reason(target_product_dict, product_dict, final_score),
                            'category_match': target_product.main_category == product.main_category
                        })
                except Exception as e:
                    logger.error(f"Ürün skorlama hatası {product.product_code}: {str(e)}")
                    continue

            # Sıralama ve çeşitlilik
            alternatives.sort(key=lambda x: x['final_score'], reverse=True)
            diverse_alternatives = self._ensure_diversity(alternatives, limit)

            return {
                'alternatives': diverse_alternatives,
                'target_product': {
                    'code': target_product.product_code,
                    'name': target_product.product_name,
                    'category': target_product.main_category
                },
                'recommendation_stats': {
                    'total_found': len(alternatives),
                    'returned': len(diverse_alternatives),
                    'avg_score': round(np.mean([alt['final_score'] for alt in diverse_alternatives]), 2) if diverse_alternatives else 0
                }
            }

        except Exception as e:
            logger.error(f"Alternatif ürün önerisi hatası: {str(e)}")
            return None

    def get_user_recommendations(self, user_data, categories=None, limit=6):
        """
        VIEW'e uyumlu kişiselleştirilmiş öneriler
        """
        try:
            # Ürün havuzunu belirle
            products_query = ProductFeatures.objects.filter(is_valid_for_analysis=True)
            
            if categories:
                category_filters = categories.split(',')
                category_q = None
                from django.db.models import Q
                for cat in category_filters:
                    if category_q is None:
                        category_q = Q(main_category__icontains=cat.strip())
                    else:
                        category_q |= Q(main_category__icontains=cat.strip())
                products_query = products_query.filter(category_q)

            products = products_query[:200]  # Performans için sınırla

            # Skorlama
            recommendations = []
            for product in products:
                try:
                    product_dict = self._convert_product_to_dict(product)
                    ml_score = self.get_personalized_score(user_data, product_dict)
                    
                    # Kişiselleştirme bonusu
                    personalization_bonus = self._calculate_personalization_bonus(user_data, product_dict)
                    
                    final_score = ml_score + personalization_bonus
                    final_score = max(0, min(10, final_score))
                    
                    recommendations.append({
                        'product': product,
                        'final_score': round(final_score, 2),
                        'ml_score': round(ml_score, 2),
                        'personalization_bonus': round(personalization_bonus, 2),
                        'recommendation_reason': self._get_personalization_reason(user_data, product_dict),
                        'health_benefits': self._get_health_benefits(user_data, product_dict)
                    })
                except Exception as e:
                    logger.error(f"Ürün skorlama hatası {product.product_code}: {str(e)}")
                    continue

            # En iyileri seç
            recommendations.sort(key=lambda x: x['final_score'], reverse=True)
            top_recommendations = recommendations[:limit * 2]  # Çeşitlilik için fazla al
            diverse_recommendations = self._ensure_diversity(top_recommendations, limit)

            return {
                'recommendations': diverse_recommendations,
                'user_profile_summary': self._get_user_summary(user_data),
                'recommendation_stats': {
                    'total_analyzed': len(recommendations),
                    'returned': len(diverse_recommendations),
                    'avg_score': round(np.mean([rec['final_score'] for rec in diverse_recommendations]), 2) if diverse_recommendations else 0
                }
            }

        except Exception as e:
            logger.error(f"Kişiselleştirilmiş öneri hatası: {str(e)}")
            return None

    def _calculate_personalization_bonus(self, user_data, product_data):
        """Kişiselleştirme bonusu hesapla"""
        bonus = 0.0
        
        # Yaş bazlı bonus
        age = user_data.get('age', 30)
        if age > 50 and product_data.get('fiber', 0) > 5:
            bonus += 0.3
        elif age < 30 and product_data.get('protein', 0) > 15:
            bonus += 0.3
        
        # Sağlık hedefleri bonusu
        health_goals = user_data.get('health_goals', [])
        if 'muscle_gain' in health_goals and product_data.get('protein', 0) > 20:
            bonus += 0.5
        if 'heart_health' in health_goals and not product_data.get('is_high_salt', 0):
            bonus += 0.4
        
        return min(1.0, bonus)

    def _get_personalization_reason(self, user_data, product_data):
        """Kişiselleştirme sebebi"""
        reasons = []
        
        age = user_data.get('age', 30)
        health_goals = user_data.get('health_goals', [])
        
        if age > 50 and product_data.get('fiber', 0) > 5:
            reasons.append("Yaşınız için yüksek fiber")
        if 'muscle_gain' in health_goals and product_data.get('protein', 0) > 20:
            reasons.append("Kas gelişimi hedefi")
        if 'heart_health' in health_goals and not product_data.get('is_high_salt', 0):
            reasons.append("Kalp sağlığı")
        
        return " • ".join(reasons[:2]) if reasons else "Kişiselleştirilmiş seçim"

    def _get_health_benefits(self, user_data, product_data):
        """Sağlık faydaları listesi"""
        benefits = []
        
        if product_data.get('protein', 0) > 15:
            benefits.append("Yüksek protein")
        if product_data.get('fiber', 0) > 5:
            benefits.append("Yüksek fiber")
        if not product_data.get('is_high_sugar', 0):
            benefits.append("Düşük şeker")
        if product_data.get('processing_level', 3) <= 2:
            benefits.append("Az işlenmiş")
        
        return benefits[:3]

    def _get_user_summary(self, user_data):
        """Kullanıcı profil özeti"""
        return {
            'age_group': 'genç' if user_data.get('age', 30) < 30 else 'orta yaş' if user_data.get('age', 30) < 50 else 'yaşlı',
            'bmi_category': self._get_bmi_category(user_data),
            'main_health_goals': user_data.get('health_goals', [])[:2],
            'dietary_restrictions': user_data.get('medical_conditions', [])[:2]
        }

    def _get_bmi_category(self, user_data):
        """BMI kategorisi"""
        bmi = self._calculate_bmi(user_data)
        if bmi < 18.5:
            return 'zayıf'
        elif bmi < 25:
            return 'normal'
        elif bmi < 30:
            return 'fazla kilolu'
        else:
            return 'obez'

    # Mevcut yardımcı metodları koru
    def get_personalized_score(self, user_profile, product_data):
        """Kişiselleştirilmiş skor hesapla"""
        if self.model is None:
            return self._calculate_fallback_score(user_profile, product_data)

        try:
            features = self._create_feature_vector(user_profile, product_data)
            features_df = pd.DataFrame([features])
            
            for col in self.feature_columns:
                if col not in features_df.columns:
                    features_df[col] = 0

            features_df = features_df[self.feature_columns]
            features_scaled = self.scaler.transform(features_df)
            prediction = self.model.predict(features_scaled)

            score = max(0, min(10, prediction[0]))
            return round(score, 2)

        except Exception as e:
            logger.error(f"ML skorlama hatası: {str(e)}")
            return self._calculate_fallback_score(user_profile, product_data)

    def _create_feature_vector(self, user_profile, product_data):
        """Feature vektörü oluştur"""
        features = {}

        # Kullanıcı özellikleri
        features['user_age'] = user_profile.get('age', 30)
        features['user_bmi'] = self._calculate_bmi(user_profile)
        features['user_gender_male'] = 1 if user_profile.get('gender') == 'Male' else 0
        features['user_activity_high'] = 1 if user_profile.get('activity_level') == 'high' else 0
        features['user_activity_moderate'] = 1 if user_profile.get('activity_level') == 'moderate' else 0

        # Sağlık durumu
        medical_conditions = user_profile.get('medical_conditions', [])
        features['has_diabetes'] = 1 if 'diabetes_type_2' in medical_conditions else 0
        features['has_kidney_disease'] = 1 if 'chronic_kidney_disease' in medical_conditions else 0
        features['has_hyperthyroidism'] = 1 if 'hyperthyroidism' in medical_conditions else 0
        features['has_osteoporosis'] = 1 if 'osteoporosis' in medical_conditions else 0

        # Diyet tercihleri
        diet_prefs = user_profile.get('dietary_preferences', [])
        features['prefers_high_protein'] = 1 if 'high_protein' in diet_prefs else 0
        features['prefers_low_fat'] = 1 if 'low_fat' in diet_prefs else 0
        features['is_vegan'] = 1 if 'vegan' in diet_prefs else 0

        # Sağlık hedefleri
        health_goals = user_profile.get('health_goals', [])
        features['goal_muscle_gain'] = 1 if 'muscle_gain' in health_goals else 0
        features['goal_heart_health'] = 1 if 'heart_health' in health_goals else 0
        features['goal_boost_energy'] = 1 if 'boost_energy' in health_goals else 0

        # Ürün özellikleri
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
        """ProductFeatures nesnesini dict'e çevir"""
        return {
            'product_code': product_obj.product_code,
            'product_name': product_obj.product_name,
            'main_category': product_obj.main_category,
            'processing_level': product_obj.processing_level,
            'nutrition_quality_score': product_obj.nutrition_quality_score,
            'health_score': product_obj.health_score,
            
            'energy_kcal': product_obj.get_energy_kcal(),
            'protein': product_obj.get_protein(),
            'fat': product_obj.get_fat(),
            'sugar': product_obj.get_sugar(),
            'salt': product_obj.get_salt(),
            'fiber': product_obj.get_fiber(),
            
            'is_high_sugar': 1 if product_obj.is_high_sugar() else 0,
            'is_high_salt': 1 if product_obj.is_high_salt() else 0,
            'is_high_fat': 1 if product_obj.is_high_fat() else 0,
            'is_high_protein': 1 if product_obj.is_high_protein() else 0,
            'is_high_fiber': 1 if product_obj.is_high_fiber() else 0,
            'has_risky_additives': 1 if product_obj.has_risky_additives() else 0,
            'additives_count': product_obj.get_additives_count(),
        }

    def _calculate_similarity_bonus(self, searched_product, recommended_product):
        """Benzerlik bonusu hesapla"""
        bonus = 0.0
        
        if searched_product.get('main_category') == recommended_product.get('main_category'):
            bonus += 0.5
        
        nutritional_similarity = self._calculate_nutritional_similarity(searched_product, recommended_product)
        bonus += nutritional_similarity * 0.3
        
        processing_diff = abs(
            searched_product.get('processing_level', 3) - 
            recommended_product.get('processing_level', 3)
        )
        if processing_diff <= 1:
            bonus += 0.2
        
        return min(1.0, bonus)

    def _calculate_nutritional_similarity(self, product1, product2):
        """Besin değerleri benzerliği"""
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
                max_val = max(val1, val2)
                min_val = min(val1, val2)
                similarity = min_val / max_val if max_val > 0 else 1.0
                similarities.append(similarity)
        
        return np.mean(similarities)

    def _ensure_diversity(self, scored_products, limit):
        """Çeşitlilik sağla"""
        if len(scored_products) <= limit:
            return scored_products
        
        diverse_products = []
        seen_categories = set()
        
        diverse_products.append(scored_products[0])
        seen_categories.add(scored_products[0]['product'].main_category)
        
        for product in scored_products[1:]:
            if len(diverse_products) >= limit:
                break
                
            category = product['product'].main_category
            if category not in seen_categories or len(diverse_products) < limit // 2:
                diverse_products.append(product)
                seen_categories.add(category)
        
        while len(diverse_products) < limit and len(diverse_products) < len(scored_products):
            for product in scored_products:
                if len(diverse_products) >= limit:
                    break
                if product not in diverse_products:
                    diverse_products.append(product)
                    break
        
        return diverse_products[:limit]

    def _get_recommendation_reason(self, searched_product, recommended_product, score):
        """Öneri sebebi"""
        reasons = []
        
        if score >= 8.5:
            reasons.append("Mükemmel uyum")
        elif score >= 7.0:
            reasons.append("Çok uygun")
        else:
            reasons.append("İyi seçim")
        
        if searched_product.get('main_category') == recommended_product.get('main_category'):
            reasons.append("Aynı kategori")
        
        if recommended_product.get('protein', 0) > searched_product.get('protein', 0):
            reasons.append("Daha yüksek protein")
        
        if recommended_product.get('sugar', 0) < searched_product.get('sugar', 0):
            reasons.append("Daha az şeker")
        
        return " • ".join(reasons[:3])

    def _calculate_fallback_score(self, user_profile, product_data):
        """Fallback skorlama"""
        base_score = 5.0

        nutrition_quality = product_data.get('nutrition_quality_score', 5)
        base_score += (nutrition_quality - 5) * 0.4

        processing_level = product_data.get('processing_level', 3)
        base_score -= (processing_level - 1) * 0.5

        age = user_profile.get('age', 30)
        if age > 65:
            if product_data.get('salt', 0) < 0.5:
                base_score += 0.5
            if product_data.get('fiber', 0) > 5:
                base_score += 0.5

        bmi = self._calculate_bmi(user_profile)
        if bmi > 30:
            if product_data.get('energy_kcal', 0) < 200:
                base_score += 0.8

        return max(0, min(10, base_score))

    def _calculate_bmi(self, user_profile):
        """BMI hesapla"""
        if user_profile.get('bmi'):
            return user_profile['bmi']
        
        height = user_profile.get('height', 170)
        weight = user_profile.get('weight', 70)
        
        if height and weight and height > 0:
            return round(weight / ((height/100) ** 2), 1)
        
        return 24  # Varsayılan

    def _safe_float(self, value):
        """Güvenli float dönüşümü"""
        try:
            return float(value) if value is not None else 0.0
        except (ValueError, TypeError):
            return 0.0


# Singleton instance
ml_recommendation_service = MLRecommendationService()