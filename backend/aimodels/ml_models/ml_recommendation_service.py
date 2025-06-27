import os
import logging
import numpy as np
import django
import joblib
from pathlib import Path

# Django setup
BASE_DIR = Path(__file__).resolve().parent.parent.parent
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from api.models.product_features import ProductFeatures

logger = logging.getLogger(__name__)

class MLRecommendationService:
    """
    ML Model tabanlı ürün alternatif ve kişiselleştirilmiş öneriler servisi
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
                logger.info("✅ ML recommendation model yüklendi")
            else:
                logger.warning("⚠️ ML model dosyaları bulunamadı")

        except Exception as e:
            logger.error(f"❌ Model yükleme hatası: {e}")

    def _calculate_ml_score(self, user_profile, product):
        """
        User profil ve ürün özelliklerine göre ML modelden sağlık skorunu tahmin eder
        """
        try:
            if not self.model or not self.scaler or not self.feature_columns:
                # Model yüklü değilse varsayılan hesaplama
                return float(product.health_score if hasattr(product, 'health_score') else 5.0)
            
            # Ürünün feature vectorunu oluştur
            features = []
            for feat in self.feature_columns:
                val = getattr(product, feat, 0)
                features.append(val)
            features = np.array(features).reshape(1, -1)
            features_scaled = self.scaler.transform(features)
            score = self.model.predict(features_scaled)[0]
            return float(score)
        except Exception as e:
            logger.error(f"ML skor hesaplama hatası: {e}")
            return float(product.health_score if hasattr(product, 'health_score') else 5.0)

    def _calculate_similarity_bonus(self, target_product, other_product):
        """Benzerlik bonusu hesaplama"""
        bonus = 0.0
        if target_product.main_category == other_product.main_category:
            bonus += 0.5
        if hasattr(target_product, 'sub_category') and hasattr(other_product, 'sub_category'):
            if target_product.sub_category == other_product.sub_category:
                bonus += 0.3
        return bonus

    def _calculate_improvement_bonus(self, target_product, other_product):
        """İyileştirme bonusu hesaplama"""
        if hasattr(other_product, 'health_score') and hasattr(target_product, 'health_score'):
            improvement = other_product.health_score - target_product.health_score
            return max(0, improvement * 0.1)  # Her 1 puan iyileştirme için 0.1 bonus
        return 0.0

    def _get_recommendation_reason(self, target_product, other_product, ml_score, target_score):
        """Öneri nedeni üret"""
        if ml_score > target_score + 1:
            return "Çok daha iyi sağlık skoru"
        elif ml_score > target_score:
            return "Daha iyi sağlık skoru"
        elif target_product.main_category == other_product.main_category:
            return "Aynı kategoride alternatif"
        else:
            return "Benzer özelliklerde ürün"

    # FIX 1: product_code parametresini user_profile ile değiştir
    def get_product_alternatives(self, user_profile, product_code, limit=5, min_score_threshold=6.0):
        """
        Hedef ürüne göre ML tabanlı alternatif öneriler
        View dosyasındaki get_ml_recommendations ile uyumlu
        """
        try:
            target_product = ProductFeatures.objects.get(
                product_code=product_code,
                is_valid_for_analysis=True
            )
            target_score = self._calculate_ml_score(user_profile, target_product)

            # Alternatif ürün havuzunu al
            alternative_products = self._get_alternative_products(target_product, limit * 3)

            scored_alternatives = []
            for product in alternative_products:
                try:
                    ml_score = self._calculate_ml_score(user_profile, product)
                    
                    # Minimum eşiği kontrol et ve hedef skordan daha iyi olsun
                    if ml_score >= min_score_threshold and ml_score > target_score:
                        similarity_bonus = self._calculate_similarity_bonus(target_product, product)
                        improvement_bonus = self._calculate_improvement_bonus(target_product, product)
                        final_score = ml_score + similarity_bonus + improvement_bonus
                        final_score = max(0, min(10, final_score))

                        scored_alternatives.append({
                            'product': product,
                            'final_score': round(final_score, 2),
                            'ml_score': round(ml_score, 2),
                            'target_score': round(target_score, 2),
                            'score_improvement': round(ml_score - target_score, 2),
                            'similarity_bonus': round(similarity_bonus, 2),
                            'improvement_bonus': round(improvement_bonus, 2),
                            'reason': self._get_recommendation_reason(target_product, product, ml_score, target_score),
                            'category_match': target_product.main_category == product.main_category
                        })
                except Exception as e:
                    logger.error(f"Ürün skorlama hatası {product.product_code}: {e}")
                    continue

            # Skora göre sırala
            scored_alternatives.sort(key=lambda x: x['final_score'], reverse=True)

            # Yeterli alternatif bulunamazsa eşiği düşür
            if len(scored_alternatives) < limit and min_score_threshold > 5.0:
                return self.get_product_alternatives(
                    user_profile, product_code, limit, min_score_threshold - 0.5
                )

            return {
                'alternatives': scored_alternatives[:limit],
                'target_product': {
                    'code': target_product.product_code,
                    'name': target_product.product_name,
                    'category': target_product.main_category,
                    'user_score': round(target_score, 2)
                },
                'recommendation_stats': {
                    'total_evaluated': len(alternative_products),
                    'qualified_alternatives': len(scored_alternatives),
                    'avg_score_improvement': round(
                        np.mean([alt['score_improvement'] for alt in scored_alternatives]), 2
                    ) if scored_alternatives else 0
                }
            }

        except ProductFeatures.DoesNotExist:
            logger.error(f"Hedef ürün bulunamadı: {product_code}")
            return None
        except Exception as e:
            logger.error(f"Alternatif öneri hatası: {e}")
            return None

    def _get_alternative_products(self, target_product, count=15):
        """Alternatif ürün havuzu oluştur"""
        # Önce aynı kategoriden ürünler
        same_category = ProductFeatures.objects.filter(
            main_category=target_product.main_category,
            is_valid_for_analysis=True,
            health_score__gte=5
        ).exclude(product_code=target_product.product_code).order_by('-health_score')[:count//2]

        # Sonra diğer kategorilerden benzer ürünler
        other_category = ProductFeatures.objects.filter(
            is_valid_for_analysis=True,
            health_score__gte=6
        ).exclude(
            main_category=target_product.main_category
        ).exclude(
            product_code=target_product.product_code
        ).order_by('-health_score')[:count//2]

        return list(same_category) + list(other_category)

    # FIX 2: Eksik olan get_user_recommendations metodunu ekle
    def get_user_recommendations(self, user_data, categories=None, limit=6):
        """
        Genel kişiselleştirilmiş öneriler
        View dosyasındaki get_ml_recommendations ile uyumlu
        """
        try:
            # Kategori filtreleme
            products_qs = ProductFeatures.objects.filter(
                is_valid_for_analysis=True, 
                health_score__gte=5
            ).order_by('-health_score')
            
            if categories:
                category_list = [cat.strip() for cat in categories.split(',')]
                products_qs = products_qs.filter(main_category__in=category_list)

            products = list(products_qs[:limit * 5])  # Geniş havuz

            recommendations = []
            for product in products:
                try:
                    ml_score = self._calculate_ml_score(user_data, product)
                    if ml_score >= 5.0:  # Minimum eşik
                        # Kişiselleştirme bonusu hesapla
                        personalization_bonus = self._calculate_personalization_bonus(user_data, product)
                        final_score = ml_score + personalization_bonus
                        final_score = max(0, min(10, final_score))

                        recommendations.append({
                            'product': product,
                            'ml_score': round(ml_score, 2),
                            'final_score': round(final_score, 2),
                            'personalization_bonus': round(personalization_bonus, 2),
                            'recommendation_reason': self._get_personalization_reason(user_data, product),
                            'health_benefits': self._get_health_benefits(product)
                        })
                except Exception as e:
                    logger.error(f"Kişiselleştirilmiş öneri hesaplama hatası {product.product_code}: {e}")
                    continue

            # Skora göre sırala ve limitle
            recommendations.sort(key=lambda x: x['final_score'], reverse=True)
            recommendations = recommendations[:limit]

            # Kullanıcı profili özeti
            user_profile_summary = {
                'user_preferences': user_data.get('preferences', {}),
                'health_conditions': user_data.get('health_conditions', []),
                'dietary_restrictions': user_data.get('dietary_restrictions', [])
            }

            # İstatistikler
            recommendation_stats = {
                'total_evaluated': len(products),
                'total_recommended': len(recommendations),
                'avg_score': round(
                    np.mean([rec['final_score'] for rec in recommendations]), 2
                ) if recommendations else 0,
                'categories_included': len(set(rec['product'].main_category for rec in recommendations))
            }

            return {
                'recommendations': recommendations,
                'user_profile_summary': user_profile_summary,
                'recommendation_stats': recommendation_stats
            }
        except Exception as e:
            logger.error(f"Kişiselleştirilmiş öneri hatası: {e}")
            return {
                'recommendations': [],
                'user_profile_summary': {},
                'recommendation_stats': {}
            }

    def _calculate_personalization_bonus(self, user_data, product):
        """Kullanıcı verilerine göre kişiselleştirme bonusu hesapla"""
        bonus = 0.0
        
        # Sağlık durumlarına göre bonus
        health_conditions = user_data.get('health_conditions', [])
        if 'diabetes' in health_conditions and hasattr(product, 'sugar_content'):
            if getattr(product, 'sugar_content', 100) < 5:  # Düşük şeker
                bonus += 0.5
        
        if 'hypertension' in health_conditions and hasattr(product, 'sodium_content'):
            if getattr(product, 'sodium_content', 1000) < 200:  # Düşük sodyum
                bonus += 0.5
        
        # Tercihler
        preferences = user_data.get('preferences', {})
        if preferences.get('organic', False) and hasattr(product, 'is_organic'):
            if getattr(product, 'is_organic', False):
                bonus += 0.3
        
        if preferences.get('high_protein', False) and hasattr(product, 'protein_content'):
            if getattr(product, 'protein_content', 0) > 10:
                bonus += 0.3
        
        # Diyet kısıtlamaları
        dietary_restrictions = user_data.get('dietary_restrictions', [])
        if 'gluten_free' in dietary_restrictions and hasattr(product, 'is_gluten_free'):
            if getattr(product, 'is_gluten_free', False):
                bonus += 0.4
        
        if 'vegan' in dietary_restrictions and hasattr(product, 'is_vegan'):
            if getattr(product, 'is_vegan', False):
                bonus += 0.4
        
        return min(bonus, 1.5)  # Maksimum 1.5 bonus

    def _get_personalization_reason(self, user_data, product):
        """Kişiselleştirme nedenini açıkla"""
        reasons = []
        
        health_conditions = user_data.get('health_conditions', [])
        if 'diabetes' in health_conditions and hasattr(product, 'sugar_content'):
            if getattr(product, 'sugar_content', 100) < 5:
                reasons.append("Düşük şeker içeriği")
        
        if 'hypertension' in health_conditions and hasattr(product, 'sodium_content'):
            if getattr(product, 'sodium_content', 1000) < 200:
                reasons.append("Düşük sodyum içeriği")
        
        preferences = user_data.get('preferences', {})
        if preferences.get('high_protein', False) and hasattr(product, 'protein_content'):
            if getattr(product, 'protein_content', 0) > 10:
                reasons.append("Yüksek protein")
        
        dietary_restrictions = user_data.get('dietary_restrictions', [])
        if 'vegan' in dietary_restrictions and hasattr(product, 'is_vegan'):
            if getattr(product, 'is_vegan', False):
                reasons.append("Vegan uyumlu")
        
        if reasons:
            return ", ".join(reasons)
        else:
            return "Genel sağlık skoru yüksek"

    def _get_health_benefits(self, product):
        """Ürünün sağlık faydalarını listele"""
        benefits = []
        
        if hasattr(product, 'fiber_content') and getattr(product, 'fiber_content', 0) > 3:
            benefits.append("Yüksek lif")
        
        if hasattr(product, 'protein_content') and getattr(product, 'protein_content', 0) > 10:
            benefits.append("Yüksek protein")
        
        if hasattr(product, 'sugar_content') and getattr(product, 'sugar_content', 100) < 5:
            benefits.append("Düşük şeker")
        
        if hasattr(product, 'sodium_content') and getattr(product, 'sodium_content', 1000) < 200:
            benefits.append("Düşük sodyum")
        
        if hasattr(product, 'vitamin_content') and getattr(product, 'vitamin_content', 0) > 5:
            benefits.append("Zengin vitamin")
        
        if benefits:
            return ", ".join(benefits)
        else:
            return "Dengeli besin değerleri"

# Service instance singleton
ml_recommendation_service = MLRecommendationService()