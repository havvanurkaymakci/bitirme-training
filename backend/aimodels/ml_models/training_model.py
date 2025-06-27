
# backend/aimodels/ml_models/training_model.py

import os
import sys
import django
from pathlib import Path

# Dosya konumu: D:\bitirme\Web-Page\backend\aimodels\ml_models\training_model.py
# Proje ana dizini: D:\bitirme\Web-Page\backend
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # 3 seviye yukarı
sys.path.insert(0, str(BASE_DIR))

# Django ayarları
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

# Geri kalan ML kodları
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
import joblib

from api.models.product_features import ProductFeatures

class PersonalizedHealthScoreModel:
    """
    Hibrit sistem için ML modeli - Kişiselleştirilmiş sağlık skoru hesaplama
    """
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.feature_columns = []
        self.user_profile_features = {}
        
    def load_user_data(self, file_path):
        """Kullanıcı verilerini yükle ve işle"""
        print("Kullanıcı verileri yükleniyor...")
        users_df = pd.read_csv(file_path)
        
        # Çoklu değerleri işle
        users_df['medical_conditions_list'] = users_df['medical_conditions'].fillna('').str.split('|')
        users_df['allergies_list'] = users_df['allergies'].fillna('').str.split('|')
        users_df['dietary_preferences_list'] = users_df['dietary_preferences'].fillna('').str.split('|')
        users_df['health_goals_list'] = users_df['health_goals'].fillna('').str.split('|')
        
        print(f"Toplam {len(users_df)} kullanıcı yüklendi")
        return users_df
    
    def load_product_data(self):
        """Django modelinden ürün verilerini yükle"""
        print("Ürün verileri Django modelinden yükleniyor...")
        
        products = ProductFeatures.objects.filter(is_valid_for_analysis=True)
        product_data = []
        
        for product in products:
            data = {
                'product_code': product.product_code,
                'product_name': product.product_name,
                'main_category': product.main_category,
                'processing_level': product.processing_level,
                'nutrition_quality_score': product.nutrition_quality_score,
                'health_score': product.health_score,
                'data_completeness_score': product.data_completeness_score,
                
                # Besin değerleri
                'energy_kcal': product.get_energy_kcal(),
                'protein': product.get_protein(),
                'fat': product.get_fat(),
                'sugar': product.get_sugar(),
                'salt': product.get_salt(),
                'fiber': product.get_fiber(),
                
                # Sağlık göstergeleri
                'is_high_sugar': 1 if product.is_high_sugar() else 0,
                'is_high_salt': 1 if product.is_high_salt() else 0,
                'is_high_fat': 1 if product.is_high_fat() else 0,
                'is_high_protein': 1 if product.is_high_protein() else 0,
                'is_high_fiber': 1 if product.is_high_fiber() else 0,
                
                # Nutriscore
                'nutriscore_numeric': product.get_nutriscore_numeric() or 0,
                
                # Katkı maddeleri
                'additives_count': product.get_additives_count(),
                'has_risky_additives': 1 if product.has_risky_additives() else 0,
            }
            product_data.append(data)
        
        products_df = pd.DataFrame(product_data)
        print(f"Toplam {len(products_df)} ürün yüklendi")
        return products_df
    
    def generate_personalized_scores(self, users_df, products_df):
        """Her kullanıcı-ürün çifti için kişiselleştirilmiş sağlık skoru hesapla"""
        print("Kişiselleştirilmiş sağlık skorları hesaplanıyor...")
        
        training_data = []
        
        for user_idx, user in users_df.iterrows():
            if user_idx % 50 == 0:
                print(f"İşlenen kullanıcı: {user_idx + 1}/{len(users_df)}")
            
            # Her kullanıcı için tüm ürünleri değerlendir (veya örneklem al)
            sample_size = min(100, len(products_df))  # Her kullanıcı için 100 ürün örneği
            product_sample = products_df.sample(n=sample_size, random_state=user_idx)
            
            for _, product in product_sample.iterrows():
                # Kişiselleştirilmiş skor hesapla
                personalized_score = self._calculate_personalized_health_score(user, product)
                
                # Feature vektörü oluştur
                features = self._create_combined_features(user, product)
                features['personalized_health_score'] = personalized_score
                
                training_data.append(features)
        
        training_df = pd.DataFrame(training_data)
        print(f"Toplam {len(training_df)} eğitim verisi oluşturuldu")
        return training_df
    
    def _calculate_personalized_health_score(self, user, product):
        """Kullanıcı profili ve ürün özelliklerine göre kişiselleştirilmiş sağlık skoru (0-10)"""
        
        base_score = 5.0  # Başlangıç skoru
        
        # 1. Temel ürün kalitesi (30% ağırlık)
        quality_score = product['nutrition_quality_score'] / 10.0 * 3
        base_score += quality_score - 1.5  # -1.5 ile +1.5 arası
        
        # 2. İşlenmişlik cezası (20% ağırlık)
        processing_penalty = (product['processing_level'] - 1) * 0.5  # 0, 0.5, 1.0, 1.5
        base_score -= processing_penalty
        
        # 3. Yaş faktörü (10% ağırlık)
        age_factor = self._get_age_based_adjustment(user['age'], product)
        base_score += age_factor
        
        # 4. BMI ve sağlık durumu faktörü (25% ağırlık)
        health_factor = self._get_health_based_adjustment(user, product)
        base_score += health_factor
        
        # 5. Diyet ve hedef uyumu (15% ağırlık)
        preference_factor = self._get_preference_based_adjustment(user, product)
        base_score += preference_factor
        
        # Skoru 0-10 arasında sınırla
        final_score = max(0, min(10, base_score))
        
        return round(final_score, 2)
    
    def _get_age_based_adjustment(self, age, product):
        """Yaşa göre ayarlama"""
        adjustment = 0
        
        if age > 65:  # Yaşlılar için
            if product['salt'] < 0.5:
                adjustment += 0.3
            if product['fiber'] > 3:
                adjustment += 0.2
        elif age < 30:  # Gençler için
            if product['protein'] > 15:
                adjustment += 0.2
            if product['energy_kcal'] > 250:
                adjustment += 0.1
        
        return adjustment
    
    def _get_health_based_adjustment(self, user, product):
        """Sağlık durumu ve BMI'ya göre ayarlama"""
        adjustment = 0
        
        # BMI ayarlaması
        bmi = user['bmi']
        if bmi > 30:  # Obez
            if product['energy_kcal'] < 200:
                adjustment += 0.8
            if product['is_high_sugar'] == 0:
                adjustment += 0.5
            if product['fat'] < 10:
                adjustment += 0.3
        elif bmi < 18.5:  # Zayıf
            if product['energy_kcal'] > 300:
                adjustment += 0.6
            if product['protein'] > 20:
                adjustment += 0.4
        
        # Sağlık durumu ayarlaması
        medical_conditions = user['medical_conditions_list']
        if medical_conditions and medical_conditions != ['']:
            for condition in medical_conditions:
                if condition == 'diabetes_type_2':
                    if product['sugar'] > 15:
                        adjustment -= 2.0  # Büyük ceza
                    elif product['sugar'] < 5:
                        adjustment += 0.8
                    if product['fiber'] > 5:
                        adjustment += 0.5
                
                elif condition == 'hyperthyroidism':
                    if product['is_high_salt']:
                        adjustment -= 1.2
                    elif product['salt'] < 0.5:
                        adjustment += 0.4
                
                elif condition == 'chronic_kidney_disease':
                    if product['protein'] > 20:
                        adjustment -= 1.5
                    if product['is_high_salt']:
                        adjustment -= 1.8
                
                elif condition == 'osteoporosis':
                    if product['protein'] > 12:
                        adjustment += 0.6
        
        return adjustment
    
    def _get_preference_based_adjustment(self, user, product):
        """Diyet tercihleri ve hedeflere göre ayarlama"""
        adjustment = 0
        
        # Diyet tercihleri
        diet_prefs = user['dietary_preferences_list']
        if diet_prefs and diet_prefs != ['']:
            for pref in diet_prefs:
                if pref == 'high_protein' and product['protein'] > 15:
                    adjustment += 0.5
                elif pref == 'low_fat' and product['fat'] < 5:
                    adjustment += 0.4
                elif pref == 'vegan':  # Vegan uyumluluğu (basit kontrol)
                    adjustment += 0.3
        
        # Sağlık hedefleri
        health_goals = user['health_goals_list']
        if health_goals and health_goals != ['']:
            for goal in health_goals:
                if goal == 'muscle_gain' and product['is_high_protein']:
                    adjustment += 0.7
                elif goal == 'heart_health':
                    if product['fiber'] > 5:
                        adjustment += 0.4
                    if product['is_high_salt'] == 0:
                        adjustment += 0.3
                elif goal == 'boost_energy' and product['energy_kcal'] > 200:
                    adjustment += 0.3
        
        # Aktivite seviyesi
        activity = user['activity_level']
        if activity == 'high':
            if product['protein'] > 12:
                adjustment += 0.3
            if product['energy_kcal'] > 250:
                adjustment += 0.2
        elif activity == 'low':
            if product['energy_kcal'] < 150:
                adjustment += 0.3
        
        return adjustment
    
    def _create_combined_features(self, user, product):
        """Kullanıcı ve ürün özelliklerini birleştir"""
        features = {}
        
        # Kullanıcı özellikleri
        features['user_age'] = user['age']
        features['user_bmi'] = user['bmi']
        features['user_gender_male'] = 1 if user['gender'] == 'Male' else 0
        features['user_activity_high'] = 1 if user['activity_level'] == 'high' else 0
        features['user_activity_moderate'] = 1 if user['activity_level'] == 'moderate' else 0
        
        # Sağlık durumu binary features
        medical_conditions = user['medical_conditions_list'] if user['medical_conditions_list'] != [''] else []
        features['has_diabetes'] = 1 if 'diabetes_type_2' in medical_conditions else 0
        features['has_kidney_disease'] = 1 if 'chronic_kidney_disease' in medical_conditions else 0
        features['has_hyperthyroidism'] = 1 if 'hyperthyroidism' in medical_conditions else 0
        features['has_osteoporosis'] = 1 if 'osteoporosis' in medical_conditions else 0
        
        # Diyet tercihleri
        diet_prefs = user['dietary_preferences_list'] if user['dietary_preferences_list'] != [''] else []
        features['prefers_high_protein'] = 1 if 'high_protein' in diet_prefs else 0
        features['prefers_low_fat'] = 1 if 'low_fat' in diet_prefs else 0
        features['is_vegan'] = 1 if 'vegan' in diet_prefs else 0
        
        # Sağlık hedefleri
        health_goals = user['health_goals_list'] if user['health_goals_list'] != [''] else []
        features['goal_muscle_gain'] = 1 if 'muscle_gain' in health_goals else 0
        features['goal_heart_health'] = 1 if 'heart_health' in health_goals else 0
        features['goal_boost_energy'] = 1 if 'boost_energy' in health_goals else 0
        
        # Ürün özellikleri (direkt)
        features['product_energy'] = product['energy_kcal']
        features['product_protein'] = product['protein']
        features['product_fat'] = product['fat']
        features['product_sugar'] = product['sugar']
        features['product_salt'] = product['salt']
        features['product_fiber'] = product['fiber']
        features['product_processing_level'] = product['processing_level']
        features['product_nutrition_quality'] = product['nutrition_quality_score']
        features['product_health_score'] = product['health_score']
        features['product_additives_count'] = product['additives_count']
        
        # Ürün binary features
        features['product_high_sugar'] = product['is_high_sugar']
        features['product_high_salt'] = product['is_high_salt']
        features['product_high_fat'] = product['is_high_fat']
        features['product_high_protein'] = product['is_high_protein']
        features['product_high_fiber'] = product['is_high_fiber']
        features['product_has_risky_additives'] = product['has_risky_additives']
        
        return features
    
    def train_model(self, training_df):
        """Modeli eğit"""
        print("Model eğitimi başlıyor...")
        
        # Feature ve target ayır
        X = training_df.drop('personalized_health_score', axis=1)
        y = training_df['personalized_health_score']
        
        # Feature isimlerini sakla
        self.feature_columns = X.columns.tolist()
        
        # Veriyi normalize et
        X_scaled = self.scaler.fit_transform(X)
        
        # Train-test split
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42
        )
        
        # Model parametrelerini optimize et
        param_grid = {
            'n_estimators': [100, 200],
            'max_depth': [10, 15, 20],
            'min_samples_split': [5, 10],
            'random_state': [42]
        }
        
        rf = RandomForestRegressor()
        grid_search = GridSearchCV(rf, param_grid, cv=5, scoring='r2', n_jobs=-1)
        grid_search.fit(X_train, y_train)
        
        self.model = grid_search.best_estimator_
        
        # Test seti değerlendirmesi
        y_pred = self.model.predict(X_test)
        
        mse = mean_squared_error(y_test, y_pred)
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        print(f"\n=== Model Performansı ===")
        print(f"En iyi parametreler: {grid_search.best_params_}")
        print(f"MSE: {mse:.4f}")
        print(f"MAE: {mae:.4f}")
        print(f"R²: {r2:.4f}")
        
        # Feature importance
        feature_importance = pd.DataFrame({
            'feature': self.feature_columns,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        print(f"\n=== En Önemli 10 Özellik ===")
        print(feature_importance.head(10))
        
        return {
            'mse': mse,
            'mae': mae,
            'r2': r2,
            'best_params': grid_search.best_params_,
            'feature_importance': feature_importance
        }
    
    def predict_health_score(self, user_features, product_features):
        """Yeni bir kullanıcı-ürün çifti için sağlık skoru tahmin et"""
        if self.model is None:
            raise ValueError("Model henüz eğitilmedi!")
        
        # Feature vektörü oluştur
        combined_features = self._create_combined_features(user_features, product_features)
        
        # DataFrame'e çevir ve eksik kolonları ekle
        features_df = pd.DataFrame([combined_features])
        for col in self.feature_columns:
            if col not in features_df.columns:
                features_df[col] = 0
        
        # Sıralamayı düzelt
        features_df = features_df[self.feature_columns]
        
        # Normalize et ve tahmin yap
        features_scaled = self.scaler.transform(features_df)
        prediction = self.model.predict(features_scaled)
        
        return max(0, min(10, prediction[0]))
    
    def save_model(self, model_dir='models'):
        """Eğitilmiş modeli kaydet"""
        if not os.path.exists(model_dir):
            os.makedirs(model_dir)
        
        print(f"Model {model_dir} klasörüne kaydediliyor...")
        
        joblib.dump(self.model, f'{model_dir}/personalized_health_model.joblib')
        joblib.dump(self.scaler, f'{model_dir}/health_scaler.joblib')
        joblib.dump(self.feature_columns, f'{model_dir}/health_feature_columns.joblib')
        
        print("Model başarıyla kaydedildi!")
    
    def load_model(self, model_dir='models'):
        """Kaydedilmiş modeli yükle"""
        print("Model yükleniyor...")
        
        self.model = joblib.load(f'{model_dir}/personalized_health_model.joblib')
        self.scaler = joblib.load(f'{model_dir}/health_scaler.joblib')
        self.feature_columns = joblib.load(f'{model_dir}/health_feature_columns.joblib')
        
        print("Model başarıyla yüklendi!")

def main():
    """Ana eğitim fonksiyonu"""
    print("=== Kişiselleştirilmiş Sağlık Skoru Modeli Eğitimi ===")
    
    # Model instance
    model = PersonalizedHealthScoreModel()
    
    # Veri yükleme
    users_df = model.load_user_data("D://bitirme//data//sample_user_profiles.csv")
    products_df = model.load_product_data()
    
    # Training verisi oluşturma
    training_df = model.generate_personalized_scores(users_df, products_df)
    
    # Model eğitimi
    results = model.train_model(training_df)
    
    # Model kaydetme
    model.save_model()
    
    print("\n=== Eğitim Tamamlandı ===")
    print("Model web uygulamasında kullanılmaya hazır!")
    
    return model, results

if __name__ == "__main__":
    trained_model, training_results = main()