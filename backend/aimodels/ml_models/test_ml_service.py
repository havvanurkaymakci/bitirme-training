# test_ml_recommendation.py
# ML recommendation servisini test et

import os
import sys
import django
from pathlib import Path

# Django setup
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from aimodels.ml_models.ml_recommendation_service import ml_recommendation_service

def test_ml_recommendation():
    """ML recommendation servisini test et"""
    
    print("=== ML Recommendation Service Test ===")
    print(f"Model durumu: {'✅ Yüklendi' if ml_recommendation_service.model else '❌ Fallback modu aktif'}")
    print(f"Scaler durumu: {'✅ Yüklendi' if ml_recommendation_service.scaler else '❌ Yok'}")
    print(f"Feature sayısı: {len(ml_recommendation_service.feature_columns) if ml_recommendation_service.feature_columns else 0}")
    print()

    # Test kullanıcı profilleri
    test_users = [
        {
            'name': 'Diyabetli Kullanıcı',
            'profile': {
                'age': 45,
                'gender': 'Male',
                'height': 180,
                'weight': 85,
                'bmi': 26.2,
                'activity_level': 'moderate',
                'medical_conditions': ['diabetes_type_2'],
                'dietary_preferences': ['low_fat', 'high_protein'],
                'health_goals': ['heart_health', 'weight_management']
            }
        },
        {
            'name': 'Genç Sporcu',
            'profile': {
                'age': 25,
                'gender': 'Female',
                'height': 165,
                'weight': 60,
                'bmi': 22.0,
                'activity_level': 'high',
                'medical_conditions': [],
                'dietary_preferences': ['high_protein', 'vegan'],
                'health_goals': ['muscle_gain', 'boost_energy']
            }
        },
        {
            'name': 'Böbrek Hastası',
            'profile': {
                'age': 55,
                'gender': 'Male',
                'height': 175,
                'weight': 78,
                'bmi': 25.5,
                'activity_level': 'low',
                'medical_conditions': ['chronic_kidney_disease'],
                'dietary_preferences': ['low_fat'],
                'health_goals': ['heart_health']
            }
        }
    ]

    # Test edilecek ürün kodları (gerçek kodlarla değiştirin)
    test_products = [
        "80052760",  # Örnek ürün kodu 1
        "40822938",  # Örnek ürün kodu 2
        "8690504065395",  # Örnek ürün kodu 3
    ]

    # Her kullanıcı için test
    for user_data in test_users:
        print(f"\n{'='*60}")
        print(f"👤 {user_data['name']} için test")
        print(f"   Yaş: {user_data['profile']['age']}, BMI: {user_data['profile']['bmi']}")
        print(f"   Sağlık durumu: {', '.join(user_data['profile']['medical_conditions']) if user_data['profile']['medical_conditions'] else 'Yok'}")
        print(f"   Hedefler: {', '.join(user_data['profile']['health_goals'])}")
        print(f"{'='*60}")

        for product_code in test_products:
            print(f"\n🔍 Ürün kodu: {product_code}")
            
            try:
                result = ml_recommendation_service.get_product_alternatives(
                    user_profile=user_data['profile'],
                    target_product_code=product_code,
                    limit=3,
                    min_score_threshold=6.0
                )
                
                if result:
                    target = result['target_product']
                    stats = result['recommendation_stats']
                    alternatives = result['alternatives']
                    
                    print(f"   📦 Hedef ürün: {target['name'][:40]}...")
                    print(f"   📊 Hedef ürün skoru: {target['user_score']}")
                    print(f"   📈 Değerlendirilen ürün: {stats['total_evaluated']}")
                    print(f"   ✅ Uygun alternatif: {stats['qualified_alternatives']}")
                    
                    if alternatives:
                        print(f"   📈 Ortalama iyileştirme: +{stats['avg_score_improvement']}")
                        print(f"\n   🏆 En iyi alternatifler:")
                        
                        for i, alt in enumerate(alternatives, 1):
                            product = alt['product']
                            print(f"   {i}. {product.product_name[:45]}...")
                            print(f"      🎯 Final skor: {alt['final_score']} (ML: {alt['ml_score']}, İyileştirme: +{alt['score_improvement']})")
                            print(f"      💡 Sebep: {alt['reason']}")
                            print(f"      📂 Kategori: {product.main_category}")
                            print(f"      🏷️ Aynı kategori: {'✅' if alt['category_match'] else '❌'}")
                            print()
                    else:
                        print("   ⚠️ Hiç uygun alternatif bulunamadı")
                        
                else:
                    print("   ❌ Ürün bulunamadı veya hata oluştu")
                    
            except Exception as e:
                print(f"   💥 Test hatası: {e}")
                
            print("-" * 40)

def test_feature_creation():
    """Feature vector oluşturma testı"""
    print("\n=== Feature Vector Test ===")
    
    test_profile = {
        'age': 30,
        'gender': 'Female',
        'height': 165,
        'weight': 60,
        'activity_level': 'moderate',
        'medical_conditions': ['diabetes_type_2'],
        'dietary_preferences': ['vegan', 'high_protein'],
        'health_goals': ['heart_health', 'muscle_gain']
    }
    
    # Mock product için basit bir sınıf
    class MockProduct:
        def __init__(self):
            self.product_code = "test_code"
            self.product_name = "Test Product"
            self.main_category = "test_category"
            self.processing_level = 2
            self.nutrition_quality_score = 7.5
            self.health_score = 6.8
            
        def get_energy_kcal(self): return 150
        def get_protein(self): return 12.5
        def get_fat(self): return 8.0
        def get_sugar(self): return 15.0
        def get_salt(self): return 1.2
        def get_fiber(self): return 3.5
        def get_additives_count(self): return 2
        def is_high_sugar(self): return False
        def is_high_salt(self): return False
        def is_high_fat(self): return False
        def is_high_protein(self): return True
        def is_high_fiber(self): return False
        def has_risky_additives(self): return False
    
    mock_product = MockProduct()
    
    try:
        features = ml_recommendation_service._create_feature_vector(test_profile, mock_product)
        
        print("✅ Feature vector başarıyla oluşturuldu!")
        print(f"📊 Toplam feature sayısı: {len(features)}")
        print("\n🔍 Örnek feature'lar:")
        
        sample_features = list(features.items())[:10]
        for key, value in sample_features:
            print(f"   {key}: {value}")
            
        if len(features) > 10:
            print(f"   ... ve {len(features) - 10} tane daha")
            
    except Exception as e:
        print(f"❌ Feature vector oluşturma hatası: {e}")

def main():
    """Ana test fonksiyonu"""
    print("🚀 ML Recommendation Service Test Başlıyor...\n")
    
    # Temel testler
    test_ml_recommendation()
    
    # Feature test
    test_feature_creation()
    
    print("\n" + "="*60)
    print("✅ Tüm testler tamamlandı!")
    print("="*60)

if __name__ == "__main__":
    main()