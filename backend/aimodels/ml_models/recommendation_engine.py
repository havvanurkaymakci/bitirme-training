# backend/aimodels/ml_models/recommendation_engine.py

import os
import sys
import django
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
import joblib

# Django setup
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from api.models.product_features import ProductFeatures
from .training_model import PersonalizedHealthScoreModel

class HybridRecommendationEngine:
    """
    Hibrit Sistem için Akıllı Öneri Motoru
    - Güvenli/güvensiz fark etmeksizin tüm ürünler için çalışır
    - Kişiselleştirilmiş skor + alternatif öneriler
    - Rule-based güvenlik + ML kişiselleştirme
    """
    
    def __init__(self):
        self.health_model = PersonalizedHealthScoreModel()
        self.product_embeddings = None
        self.product_df = None
        self.similarity_matrix = None
        self.scaler = StandardScaler()
        
    def initialize(self, model_dir='models'):
        """Sistem başlatma - eğitilmiş modeli yükle"""
        print("🚀 Hibrit Öneri Sistemi başlatılıyor...")
        
        # Eğitilmiş sağlık modelini yükle
        self.health_model.load_model(model_dir)
        
        # Ürün verilerini yükle ve embedding oluştur
        self._load_and_prepare_products()
        
        print("✅ Sistem hazır!")
    
    def _load_and_prepare_products(self):
        """Ürün verilerini yükle ve benzerlik matrisi oluştur"""
        print("📦 Ürün verileri hazırlanıyor...")
        
        # Django'dan tüm ürünleri çek
        products = ProductFeatures.objects.filter(is_valid_for_analysis=True)
        product_data = []
        
        for product in products:
            data = {
                'product_code': product.product_code,
                'product_name': product.product_name,
                'main_category': product.main_category,
                'sub_category': getattr(product, 'sub_category', ''),
                'processing_level': product.processing_level,
                'nutrition_quality_score': product.nutrition_quality_score,
                'health_score': product.health_score,
                
                # Besin değerleri (normalized)
                'energy_kcal': product.get_energy_kcal(),
                'protein': product.get_protein(),
                'fat': product.get_fat(),
                'sugar': product.get_sugar(),
                'salt': product.get_salt(),
                'fiber': product.get_fiber(),
                
                # Binary features
                'is_high_sugar': 1 if product.is_high_sugar() else 0,
                'is_high_salt': 1 if product.is_high_salt() else 0,
                'is_high_fat': 1 if product.is_high_fat() else 0,
                'is_high_protein': 1 if product.is_high_protein() else 0,
                'is_high_fiber': 1 if product.is_high_fiber() else 0,
                
                # Nutri-score ve katkılar
                'nutriscore_numeric': product.get_nutriscore_numeric() or 0,
                'additives_count': product.get_additives_count(),
                'has_risky_additives': 1 if product.has_risky_additives() else 0,
            }
            product_data.append(data)
        
        self.product_df = pd.DataFrame(product_data)
        
        # Benzerlik hesaplama için embedding oluştur
        self._create_product_embeddings()
        
        print(f"✅ {len(self.product_df)} ürün hazırlandı")
    
    def _create_product_embeddings(self):
        """Ürün benzerliği için embedding vektörleri oluştur"""
        
        # Numerik özellikler seç
        embedding_features = [
            'energy_kcal', 'protein', 'fat', 'sugar', 'salt', 'fiber',
            'processing_level', 'nutrition_quality_score', 'nutriscore_numeric',
            'additives_count', 'is_high_sugar', 'is_high_salt', 'is_high_fat',
            'is_high_protein', 'is_high_fiber', 'has_risky_additives'
        ]
        
        # Eksik değerleri doldur
        embedding_data = self.product_df[embedding_features].fillna(0)
        
        # Normalize et
        self.product_embeddings = self.scaler.fit_transform(embedding_data)
        
        # Cosine similarity matrisi hesapla
        self.similarity_matrix = cosine_similarity(self.product_embeddings)
        
        print("🧠 Ürün benzerlik matrisi oluşturuldu")
    
    def get_personalized_analysis(self, user_profile, target_product_code, 
                                num_alternatives=5, include_unsafe=True):
        """
        Hibrit analiz: Hedef ürün + alternatif öneriler
        
        Args:
            user_profile: Kullanıcı profil dict'i
            target_product_code: Aranan ürünün kodu
            num_alternatives: Kaç alternatif önerilsin
            include_unsafe: Güvensiz ürünler de önerilsin mi
        
        Returns:
            {
                'target_analysis': {...},
                'alternatives': [...],
                'insights': {...}
            }
        """
        
        print(f"🎯 Hibrit analiz başlatılıyor: {target_product_code}")
        
        # Hedef ürünü bul
        target_product = self.product_df[
            self.product_df['product_code'] == target_product_code
        ]
        
        if target_product.empty:
            return {
                'error': 'Ürün bulunamadı',
                'target_analysis': None,
                'alternatives': [],
                'insights': {}
            }
        
        target_product = target_product.iloc[0]
        
        # 1. Hedef ürün analizi
        target_analysis = self._analyze_single_product(user_profile, target_product)
        
        # 2. Alternatif öneriler
        alternatives = self._get_smart_alternatives(
            user_profile, target_product, num_alternatives, include_unsafe
        )
        
        # 3. İçgörüler
        insights = self._generate_insights(user_profile, target_analysis, alternatives)
        
        return {
            'target_analysis': target_analysis,
            'alternatives': alternatives,
            'insights': insights
        }
    
    def _analyze_single_product(self, user_profile, product):
        """Tek ürün için detaylı analiz"""
        
        # Kişiselleştirilmiş sağlık skoru hesapla
        health_score = self.health_model.predict_health_score(user_profile, product)
        
        # Güvenlik durumu (rule-based logic)
        safety_status = self._check_safety_rules(user_profile, product)
        
        # Neden bu skor aldığını açıkla
        score_explanation = self._explain_health_score(user_profile, product, health_score)
        
        return {
            'product_code': product['product_code'],
            'product_name': product['product_name'],
            'category': product['main_category'],
            'personalized_health_score': round(health_score, 1),
            'safety_status': safety_status,
            'score_explanation': score_explanation,
            'nutritional_highlights': self._get_nutritional_highlights(product),
            'user_compatibility': self._assess_user_compatibility(user_profile, product)
        }
    
    def _check_safety_rules(self, user_profile, product):
        """Rule-based güvenlik kontrolü"""
        
        warnings = []
        risk_level = 'safe'
        
        # Kullanıcının sağlık durumlarını kontrol et
        medical_conditions = user_profile.get('medical_conditions_list', [])
        
        for condition in medical_conditions:
            if condition == 'diabetes_type_2':
                if product['sugar'] > 15:
                    warnings.append("⚠️ Yüksek şeker içeriği - Diyabet için riskli")
                    risk_level = 'risky'
                elif product['sugar'] > 10:
                    warnings.append("⚡ Orta seviye şeker - Dikkatli tüketin")
                    risk_level = 'moderate' if risk_level == 'safe' else risk_level
            
            elif condition == 'chronic_kidney_disease':
                if product['protein'] > 20:
                    warnings.append("⚠️ Yüksek protein - Böbrek hastalığı için riskli")
                    risk_level = 'risky'
                if product['salt'] > 1.0:
                    warnings.append("⚠️ Yüksek tuz - Böbrek hastalığı için riskli")
                    risk_level = 'risky'
            
            elif condition == 'hyperthyroidism':
                if product['is_high_salt']:
                    warnings.append("⚠️ Yüksek tuz - Hipertansiyon için riskli")
                    risk_level = 'risky'
        
        # BMI kontrolü
        bmi = user_profile.get('bmi', 25)
        if bmi > 30 and product['energy_kcal'] > 400:
            warnings.append("⚡ Yüksek kalori - Kilo kontrolü için dikkat")
            risk_level = 'moderate' if risk_level == 'safe' else risk_level
        
        return {
            'level': risk_level,
            'warnings': warnings,
            'safe_for_user': risk_level == 'safe'
        }
    
    def _get_smart_alternatives(self, user_profile, target_product, num_alternatives, include_unsafe):
        """Akıllı alternatif öneriler"""
        
        # Hedef ürünün index'ini bul
        target_idx = self.product_df[
            self.product_df['product_code'] == target_product['product_code']
        ].index[0]
        
        # Benzer ürünleri bul
        similarity_scores = self.similarity_matrix[target_idx]
        similar_indices = np.argsort(similarity_scores)[::-1][1:num_alternatives*3]  # 3x fazla al, filtreleyeceğiz
        
        alternatives = []
        
        for idx in similar_indices:
            if len(alternatives) >= num_alternatives:
                break
                
            candidate_product = self.product_df.iloc[idx]
            
            # Bu ürün için analiz yap
            analysis = self._analyze_single_product(user_profile, candidate_product)
            
            # Güvensiz ürünleri filtrele (istenirse)
            if not include_unsafe and analysis['safety_status']['level'] == 'risky':
                continue
            
            # Hedef üründen daha iyi skor alıyorsa ekle
            alternatives.append({
                **analysis,
                'similarity_score': similarity_scores[idx],
                'improvement_reason': self._why_better_alternative(
                    target_product, candidate_product, user_profile
                )
            })
        
        # Skor ve benzerliğe göre sırala
        alternatives.sort(key=lambda x: (x['personalized_health_score'], x['similarity_score']), reverse=True)
        
        return alternatives[:num_alternatives]
    
    def _explain_health_score(self, user_profile, product, score):
        """Sağlık skorunun açıklaması"""
        
        explanations = []
        
        # Pozitif faktörler
        if product['protein'] > 15 and user_profile.get('goal_muscle_gain', 0):
            explanations.append("✅ Kas gelişimi hedefiniz için yüksek protein")
        
        if product['fiber'] > 5:
            explanations.append("✅ Yüksek lif içeriği - sindirim sağlığı için iyi")
        
        if product['processing_level'] <= 2:
            explanations.append("✅ Az işlenmiş ürün - doğal besin")
        
        # Negatif faktörler
        if product['sugar'] > 15:
            explanations.append("❌ Yüksek şeker içeriği skoru düşürüyor")
        
        if product['has_risky_additives']:
            explanations.append("❌ Riskli katkı maddeleri içeriyor")
        
        # BMI uyumluluğu
        bmi = user_profile.get('bmi', 25)
        if bmi > 30 and product['energy_kcal'] < 200:
            explanations.append("✅ Kilo kontrolü için uygun kalori miktarı")
        
        return explanations
    
    def _get_nutritional_highlights(self, product):
        """Besinsel öne çıkan özellikler"""
        
        highlights = []
        
        if product['protein'] > 20:
            highlights.append(f"🥩 Yüksek Protein: {product['protein']}g")
        
        if product['fiber'] > 5:
            highlights.append(f"🌾 Yüksek Lif: {product['fiber']}g")
        
        if product['sugar'] < 5:
            highlights.append("🍯 Düşük Şeker")
        
        if product['salt'] < 0.3:
            highlights.append("🧂 Düşük Tuz")
        
        if product['energy_kcal'] < 150:
            highlights.append("⚡ Düşük Kalori")
        
        return highlights
    
    def _assess_user_compatibility(self, user_profile, product):
        """Kullanıcı uyumluluğu değerlendirmesi"""
        
        compatibility = {
            'diet_match': 0,
            'health_goal_match': 0,
            'medical_safety': 0,
            'overall_score': 0
        }
        
        # Diyet uyumluluğu
        diet_prefs = user_profile.get('dietary_preferences_list', [])
        if 'high_protein' in diet_prefs and product['protein'] > 15:
            compatibility['diet_match'] += 30
        if 'low_fat' in diet_prefs and product['fat'] < 5:
            compatibility['diet_match'] += 30
        
        # Sağlık hedefi uyumluluğu
        health_goals = user_profile.get('health_goals_list', [])
        if 'heart_health' in health_goals and product['fiber'] > 5:
            compatibility['health_goal_match'] += 25
        if 'muscle_gain' in health_goals and product['protein'] > 18:
            compatibility['health_goal_match'] += 35
        
        # Tıbbi güvenlik
        safety_status = self._check_safety_rules(user_profile, product)
        if safety_status['level'] == 'safe':
            compatibility['medical_safety'] = 100
        elif safety_status['level'] == 'moderate':
            compatibility['medical_safety'] = 60
        else:
            compatibility['medical_safety'] = 20
        
        # Genel skor
        compatibility['overall_score'] = (
            compatibility['diet_match'] * 0.3 +
            compatibility['health_goal_match'] * 0.3 +
            compatibility['medical_safety'] * 0.4
        )
        
        return compatibility
    
    def _why_better_alternative(self, target_product, alternative_product, user_profile):
        """Neden daha iyi alternatif olduğunu açıkla"""
        
        reasons = []
        
        # Besinsel karşılaştırma
        if alternative_product['protein'] > target_product['protein']:
            reasons.append(f"Daha yüksek protein ({alternative_product['protein']}g vs {target_product['protein']}g)")
        
        if alternative_product['sugar'] < target_product['sugar']:
            reasons.append(f"Daha düşük şeker ({alternative_product['sugar']}g vs {target_product['sugar']}g)")
        
        if alternative_product['processing_level'] < target_product['processing_level']:
            reasons.append("Daha az işlenmiş")
        
        if alternative_product['nutrition_quality_score'] > target_product['nutrition_quality_score']:
            reasons.append("Daha yüksek besin kalitesi skoru")
        
        # Kullanıcı odaklı nedenler
        medical_conditions = user_profile.get('medical_conditions_list', [])
        if 'diabetes_type_2' in medical_conditions and alternative_product['sugar'] < target_product['sugar']:
            reasons.append("Diyabet için daha güvenli")
        
        return reasons
    
    def _generate_insights(self, user_profile, target_analysis, alternatives):
        """Genel içgörüler ve öneriler"""
        
        insights = {
            'user_profile_summary': self._summarize_user_profile(user_profile),
            'target_product_verdict': self._get_product_verdict(target_analysis),
            'recommendation_strategy': self._get_recommendation_strategy(user_profile, alternatives),
            'health_tips': self._get_personalized_health_tips(user_profile)
        }
        
        return insights
    
    def _summarize_user_profile(self, user_profile):
        """Kullanıcı profili özeti"""
        
        age = user_profile.get('age', 0)
        bmi = user_profile.get('bmi', 25)
        medical_conditions = user_profile.get('medical_conditions_list', [])
        health_goals = user_profile.get('health_goals_list', [])
        
        summary = f"{age} yaşında, BMI: {bmi:.1f}"
        
        if medical_conditions and medical_conditions != ['']:
            summary += f", Sağlık durumu: {', '.join(medical_conditions)}"
        
        if health_goals and health_goals != ['']:
            summary += f", Hedefler: {', '.join(health_goals)}"
        
        return summary
    
    def _get_product_verdict(self, target_analysis):
        """Ürün hakkında genel değerlendirme"""
        
        score = target_analysis['personalized_health_score']
        safety = target_analysis['safety_status']['level']
        
        if safety == 'risky':
            return "⚠️ Bu ürün sağlık durumunuz için riskli olabilir"
        elif score >= 8:
            return "✅ Sizin için mükemmel bir seçim!"
        elif score >= 6:
            return "👍 İyi bir seçim, alternatifler de var"
        elif score >= 4:
            return "🤔 Orta seviye, daha iyi alternatifler mevcut"
        else:
            return "❌ Size uygun olmayabilir, alternatiflerimize bakın"
    
    def _get_recommendation_strategy(self, user_profile, alternatives):
        """Öneri stratejisi"""
        
        if not alternatives:
            return "Benzer ürünlerde daha iyi alternatif bulunamadı"
        
        best_alternative = alternatives[0]
        improvement = best_alternative['personalized_health_score']
        
        if improvement >= 8:
            return f"🌟 En iyi alternatif {improvement}/10 skor ile harika bir seçim!"
        else:
            return f"💡 {len(alternatives)} alternatif bulundu, en iyisi {improvement}/10 skor"
    
    def _get_personalized_health_tips(self, user_profile):
        """Kişiselleştirilmiş sağlık önerileri"""
        
        tips = []
        
        medical_conditions = user_profile.get('medical_conditions_list', [])
        bmi = user_profile.get('bmi', 25)
        
        if 'diabetes_type_2' in medical_conditions:
            tips.append("🍎 Şeker içeriği 5g'dan az olan ürünleri tercih edin")
            tips.append("🌾 Yüksek lifli ürünler kan şekerinizi dengelemeye yardımcı olur")
        
        if bmi > 30:
            tips.append("⚡ 200 kalori altındaki ürünleri tercih edin")
            tips.append("🥩 Protein oranı yüksek ürünler tokluk sağlar")
        
        if user_profile.get('goal_muscle_gain', 0):
            tips.append("💪 20g üzeri protein içeren ürünleri seçin")
        
        if user_profile.get('goal_heart_health', 0):
            tips.append("❤️ Düşük tuz ve yüksek lif içeren ürünler kalp sağlığına iyi gelir")
        
        return tips[:3]  # En fazla 3 öneri

# Singleton instance için
_recommendation_engine = None

def get_recommendation_engine():
    """Singleton recommendation engine"""
    global _recommendation_engine
    if _recommendation_engine is None:
        _recommendation_engine = HybridRecommendationEngine()
        _recommendation_engine.initialize()
    return _recommendation_engine

# Test fonksiyonu
def test_recommendation_system():
    """Test için örnek kullanım"""
    
    engine = get_recommendation_engine()
    
    # Örnek kullanıcı profili
    sample_user = {
        'age': 45,
        'bmi': 28.5,
        'gender': 'Male',
        'activity_level': 'moderate',
        'medical_conditions_list': ['diabetes_type_2'],
        'dietary_preferences_list': ['high_protein'],
        'health_goals_list': ['heart_health', 'weight_loss']
    }
    
    # Örnek ürün kodu (gerçek bir ürün kodu kullanın)
    sample_product_code = "20000001"  # Bu değeri gerçek bir ürün kodu ile değiştirin
    
    # Hibrit analiz
    result = engine.get_personalized_analysis(
        user_profile=sample_user,
        target_product_code=sample_product_code,
        num_alternatives=3,
        include_unsafe=True
    )
    
    print("🎯 Hibrit Analiz Sonuçları:")
    print(f"Hedef Ürün Skoru: {result['target_analysis']['personalized_health_score']}")
    print(f"Alternatif Sayısı: {len(result['alternatives'])}")
    print(f"Güvenlik Durumu: {result['target_analysis']['safety_status']['level']}")
    
    return result

if __name__ == "__main__":
    test_recommendation_system()