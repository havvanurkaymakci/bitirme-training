# backend/pipeline/feature_extractor.py

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class ProductFeatureExtractor:
    """
    İşlenmiş OpenFoodFacts verilerinden ProductFeatures modeli için özellik çıkarma sınıfı
    """
    
    def __init__(self):
        # Besin değerleri mapping'i
        self.nutrition_mapping = {
            'energy_100g': 'energy_100g',
            'fat_100g': 'fat_100g', 
            'saturated-fat_100g': 'saturated-fat_100g',
            'carbohydrates_100g': 'carbohydrates_100g',
            'sugars_100g': 'sugars_100g',
            'fiber_100g': 'fiber_100g',
            'proteins_100g': 'proteins_100g',
            'salt_100g': 'salt_100g',
            'sodium_100g': 'sodium_100g',
            'vitamin-a_100g': 'vitamin-a_100g',
            'vitamin-c_100g': 'vitamin-c_100g',
            'calcium_100g': 'calcium_100g',
            'iron_100g': 'iron_100g',
            'potassium_100g': 'potassium_100g'
        }
        
        # Alerjen kelimeleri - preprocessor'da alerjen sütunları yok, bu yüzden text'ten çıkaracağız
        self.allergen_keywords = {
            'contains_gluten': ['gluten', 'wheat', 'buğday', 'glüten'],
            'contains_milk': ['milk', 'dairy', 'süt', 'laktoz', 'lactose'],
            'contains_eggs': ['egg', 'yumurta', 'albumin'],
            'contains_soy': ['soy', 'soja', 'soya'],
            'contains_nuts': ['nuts', 'nut', 'fındık', 'ceviz', 'badem'],
            'contains_peanuts': ['peanut', 'yer fıstığı'],
            'contains_fish': ['fish', 'balık'],
            'contains_shellfish': ['shellfish', 'kabuklu', 'shrimp', 'karides'],
            'contains_sesame': ['sesame', 'susam'],
            'contains_celery': ['celery', 'kereviz'],
            'contains_mustard': ['mustard', 'hardal'],
            'contains_sulphites': ['sulphite', 'sülfür', 'sulfur']
        }
    
    def extract_nutrition_vector(self, row: pd.Series) -> Dict[str, float]:
        """Besin değerleri vektörünü çıkar"""
        nutrition_vector = {}
        
        for model_field, df_column in self.nutrition_mapping.items():
            # Önce sütunun var olup olmadığını kontrol et
            if df_column in row.index:
                try:
                    value = row[df_column]
                    # NaN kontrolü
                    if pd.notna(value) and value != '' and str(value).lower() != 'nan':
                        nutrition_vector[model_field] = float(value)
                    else:
                        nutrition_vector[model_field] = 0.0
                except (ValueError, TypeError, KeyError) as e:
                    logger.debug(f"Besin değeri dönüştürme hatası - {df_column}: {e}")
                    nutrition_vector[model_field] = 0.0
            else:
                nutrition_vector[model_field] = 0.0
        
        # Energy kcal yoksa energy'den hesapla (kJ to kcal: kJ/4.184)
        if nutrition_vector.get('energy_kcal_100g', 0) == 0 and nutrition_vector.get('energy_100g', 0) > 0:
            nutrition_vector['energy_kcal_100g'] = nutrition_vector['energy_100g'] / 4.184
        
        return nutrition_vector
    
    def extract_allergen_vector(self, row: pd.Series) -> Dict[str, int]:
        """Alerjen vektörünü çıkar - allergen text'lerden ve ingredients'tan"""
        allergen_vector = {}
        
        # Alerjen text'leri birleştir
        allergen_text = ""
        for col in ['allergens', 'allergens_en', 'traces', 'traces_en']:
            if col in row.index:
                try:
                    value = row[col]
                    if pd.notna(value) and str(value).lower() != 'nan':
                        allergen_text += " " + str(value).lower()
                except (KeyError, AttributeError):
                    continue
        
        # İçerik metni de ekle
        if 'ingredients_text' in row.index:
            try:
                value = row['ingredients_text']
                if pd.notna(value):
                    allergen_text += " " + str(value).lower()
            except (KeyError, AttributeError):
                pass
        
        # Alerjen varlığını kontrol et
        total_allergens = 0
        for allergen_field, keywords in self.allergen_keywords.items():
            contains_allergen = any(keyword in allergen_text for keyword in keywords)
            allergen_vector[allergen_field] = 1 if contains_allergen else 0
            total_allergens += allergen_vector[allergen_field]
        
        allergen_vector['total_allergens'] = total_allergens
        
        return allergen_vector
    
    def extract_additives_info(self, row: pd.Series) -> Dict[str, Any]:
        """Katkı madde bilgilerini çıkar"""
        additives_info = {}
        
        # Katkı madde sayısı
        if 'additives_n' in row.index:
            try:
                value = row['additives_n']
                if pd.notna(value):
                    additives_info['additives_count'] = int(value)
                else:
                    additives_info['additives_count'] = 0
            except (ValueError, TypeError, KeyError):
                additives_info['additives_count'] = 0
        else:
            additives_info['additives_count'] = 0
        
        # Riskli katkı madde varlığı (5'ten fazla katkı madde riskli sayılır)
        additives_info['has_risky_additives'] = 1 if additives_info['additives_count'] > 5 else 0
        
        return additives_info
    
    def extract_nutriscore_data(self, row: pd.Series) -> Dict[str, Any]:
        """Nutriscore verilerini çıkar"""
        nutriscore_data = {}
        
        # Nutriscore grade (fr veya uk'dan al)
        for grade_col in ['nutrition_grade_fr', 'nutrition_grade_uk']:
            if grade_col in row.index:
                try:
                    value = row[grade_col]
                    if pd.notna(value):
                        nutriscore_data['nutriscore_grade'] = str(value).upper()
                        break
                except (KeyError, AttributeError):
                    continue
        
        # Nutriscore numeric (fr veya uk'dan al)
        for score_col in ['nutrition-score-fr_100g', 'nutrition-score-uk_100g']:
            if score_col in row.index:
                try:
                    value = row[score_col]
                    if pd.notna(value):
                        nutriscore_data['nutriscore_numeric'] = float(value)
                        break
                except (ValueError, TypeError, KeyError):
                    continue
        
        # Eğer numeric yok ama grade varsa, grade'den tahmin et
        if 'nutriscore_numeric' not in nutriscore_data and 'nutriscore_grade' in nutriscore_data:
            grade_to_numeric = {'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5}
            grade = nutriscore_data['nutriscore_grade']
            if grade in grade_to_numeric:
                nutriscore_data['nutriscore_numeric'] = float(grade_to_numeric[grade])
        
        return nutriscore_data
    
    def extract_health_indicators(self, row: pd.Series) -> Dict[str, int]:
        """Sağlık göstergelerini çıkar - WHO ve FDA standartlarına göre"""
        health_indicators = {}
        
        # Nutrition vector'ı al
        nutrition = self.extract_nutrition_vector(row)
        
        # WHO/FDA eşik değerleri (100g başına)
        thresholds = {
            'high_calorie': 400,    # kcal
            'high_fat': 20,         # g
            'high_sugar': 22.5,     # g
            'high_salt': 1.5,       # g
            'high_protein': 12,     # g (yüksek protein için minimum)
            'high_fiber': 6         # g (yüksek fiber için minimum)
        }
        
        # Kalori kontrolü
        energy_kcal = nutrition.get('energy_kcal_100g', 0)
        if energy_kcal == 0:
            energy_kcal = nutrition.get('energy_100g', 0) / 4.184  # kJ to kcal
        health_indicators['high_calorie'] = 1 if energy_kcal > thresholds['high_calorie'] else 0
        
        # Yağ kontrolü
        health_indicators['high_fat'] = 1 if nutrition.get('fat_100g', 0) > thresholds['high_fat'] else 0
        
        # Şeker kontrolü
        health_indicators['high_sugar'] = 1 if nutrition.get('sugars_100g', 0) > thresholds['high_sugar'] else 0
        
        # Tuz kontrolü
        salt_content = nutrition.get('salt_100g', 0)
        if salt_content == 0 and nutrition.get('sodium_100g', 0) > 0:
            salt_content = nutrition.get('sodium_100g', 0) * 2.5  # Sodium to salt conversion
        health_indicators['high_salt'] = 1 if salt_content > thresholds['high_salt'] else 0
        
        # Protein kontrolü (yüksek protein iyi bir şey)
        health_indicators['high_protein'] = 1 if nutrition.get('proteins_100g', 0) > thresholds['high_protein'] else 0
        
        # Fiber kontrolü (yüksek fiber iyi bir şey)
        health_indicators['high_fiber'] = 1 if nutrition.get('fiber_100g', 0) > thresholds['high_fiber'] else 0
        
        return health_indicators
    
    def extract_macro_ratios(self, row: pd.Series) -> Dict[str, float]:
        """Makro besin oranlarını çıkar - preprocessor'dan gelen hesaplanmış değerleri kullan"""
        macro_ratios = {}
        
        # Preprocessor'dan gelen oranları kullan
        ratio_columns = ['fat_ratio', 'carb_ratio', 'protein_ratio']
        for col in ratio_columns:
            if col in row.index:
                try:
                    value = row[col]
                    if pd.notna(value):
                        # carb_ratio'yu carbohydrates_ratio olarak kaydet (model ile uyumlu)
                        if col == 'carb_ratio':
                            macro_ratios['carbohydrates_ratio'] = float(value)
                        else:
                            macro_ratios[col.replace('_ratio', '_ratio')] = float(value)
                    else:
                        macro_ratios[col] = 0.0
                except (ValueError, TypeError, KeyError):
                    macro_ratios[col] = 0.0
            else:
                macro_ratios[col] = 0.0
        
        # Şeker/karbonhidrat oranı
        if 'sugar_intensity' in row.index:
            try:
                value = row['sugar_intensity']
                if pd.notna(value):
                    macro_ratios['sugar_carb_ratio'] = float(value)
                else:
                    macro_ratios['sugar_carb_ratio'] = 0.0
            except (ValueError, TypeError, KeyError):
                macro_ratios['sugar_carb_ratio'] = 0.0
        else:
            # Manuel hesapla
            nutrition = self.extract_nutrition_vector(row)
            sugars = nutrition.get('sugars_100g', 0)
            carbs = nutrition.get('carbohydrates_100g', 0)
            if carbs > 0:
                macro_ratios['sugar_carb_ratio'] = sugars / carbs
            else:
                macro_ratios['sugar_carb_ratio'] = 0.0
        
        return macro_ratios
    
    def calculate_health_score(self, row: pd.Series) -> float:
        """Genel sağlık skorunu hesapla (0-10 arası)"""
        health_indicators = self.extract_health_indicators(row)
        nutrition = self.extract_nutrition_vector(row)
        additives = self.extract_additives_info(row)
        
        score = 5.0  # Başlangıç skoru
        
        # Negatif faktörler
        if health_indicators.get('high_calorie', 0):
            score -= 1.0
        if health_indicators.get('high_fat', 0):
            score -= 1.0
        if health_indicators.get('high_sugar', 0):
            score -= 1.5
        if health_indicators.get('high_salt', 0):
            score -= 1.5
        
        # Katkı madde cezası
        additives_count = additives.get('additives_count', 0)
        if additives_count > 0:
            score -= min(additives_count * 0.2, 2.0)  # Maksimum 2 puan ceza
        
        # Pozitif faktörler
        if health_indicators.get('high_protein', 0):
            score += 1.0
        if health_indicators.get('high_fiber', 0):
            score += 1.0
        
        # Vitamin bonusu
        vitamin_bonus = 0
        for vitamin in ['vitamin-a_100g', 'vitamin-c_100g']:
            if nutrition.get(vitamin, 0) > 0:
                vitamin_bonus += 0.5
        score += min(vitamin_bonus, 1.0)
        
        # 0-10 arasında sınırla
        return max(0.0, min(10.0, score))
    
    def calculate_nutrition_quality_score(self, row: pd.Series) -> float:
        """Besin kalitesi skorunu hesapla (0-10 arası)"""
        nutrition = self.extract_nutrition_vector(row)
        
        # Temel besin değerlerinin varlığı
        essential_nutrients = ['energy_kcal_100g', 'fat_100g', 'carbohydrates_100g', 'proteins_100g']
        present_nutrients = sum(1 for nutrient in essential_nutrients if nutrition.get(nutrient, 0) > 0)
        
        base_score = (present_nutrients / len(essential_nutrients)) * 5.0
        
        # Vitamin ve mineral bonusu
        micronutrients = ['vitamin-a_100g', 'vitamin-c_100g', 'calcium_100g', 'iron_100g']
        present_micros = sum(1 for micro in micronutrients if nutrition.get(micro, 0) > 0)
        micro_bonus = (present_micros / len(micronutrients)) * 3.0
        
        # Fiber bonusu
        fiber_bonus = min(nutrition.get('fiber_100g', 0) / 10.0, 2.0)
        
        total_score = base_score + micro_bonus + fiber_bonus
        return min(10.0, total_score)
    
    def calculate_data_completeness(self, row: pd.Series, nutrition_vector: Dict) -> float:
        """Veri tamlık skorunu hesapla"""
        # Temel besin değerleri
        essential_nutrients = ['energy_kcal_100g', 'fat_100g', 'carbohydrates_100g', 'proteins_100g']
        essential_count = sum(1 for nutrient in essential_nutrients if nutrition_vector.get(nutrient, 0) > 0)
        
        # Diğer önemli alanlar
        important_fields = ['product_name']
        important_count = 0
        for field in important_fields:
            try:
                if field in row.index and pd.notna(row[field]):
                    important_count += 1
            except KeyError:
                continue
        
        # Ek bilgi alanları
        extra_fields = ['main_category', 'brands', 'ingredients_text']
        extra_count = 0
        for field in extra_fields:
            try:
                if field in row.index and pd.notna(row[field]) and str(row[field]).strip() != '':
                    extra_count += 1
            except KeyError:
                continue
        
        # Ağırlıklı skor
        essential_weight = 0.6
        important_weight = 0.3  
        extra_weight = 0.1
        
        essential_score = (essential_count / len(essential_nutrients)) * essential_weight
        important_score = (important_count / len(important_fields)) * important_weight
        extra_score = (extra_count / len(extra_fields)) * extra_weight
        
        return essential_score + important_score + extra_score
    
    def extract_all_features(self, row: pd.Series) -> Dict[str, Any]:
        """Bir ürün için tüm özellikleri çıkar"""
        try:
            # Temel alanları kontrol et
            if 'product_name' not in row.index or pd.isna(row['product_name']):
                return None
            
            # Tüm özellik vektörlerini çıkar
            nutrition_vector = self.extract_nutrition_vector(row)
            allergen_vector = self.extract_allergen_vector(row)
            additives_info = self.extract_additives_info(row)
            nutriscore_data = self.extract_nutriscore_data(row)
            health_indicators = self.extract_health_indicators(row)
            macro_ratios = self.extract_macro_ratios(row)
            
            # Skorları hesapla
            health_score = self.calculate_health_score(row)
            nutrition_quality_score = self.calculate_nutrition_quality_score(row)
            data_completeness = self.calculate_data_completeness(row, nutrition_vector)
            
            # Processing level'ı preprocessor'dan al, yoksa tahmin et
            processing_level = 1
            if 'estimated_processing_level' in row.index:
                try:
                    value = row['estimated_processing_level']
                    if pd.notna(value):
                        processing_level = int(value)
                except (ValueError, TypeError, KeyError):
                    pass
            
            # Kategoriden main_category çıkar
            main_category = 'unknown'
            if 'main_category' in row.index:
                try:
                    value = row['main_category']
                    if pd.notna(value):
                        main_category = str(value)
                except (KeyError, AttributeError):
                    pass
            elif 'categories' in row.index:
                try:
                    value = row['categories']
                    if pd.notna(value):
                        categories = str(value).split(',')
                        if categories:
                            main_category = categories[0].strip()
                except (KeyError, AttributeError):
                    pass
            
            # Brand bilgisi
            main_brand = None
            if 'brands' in row.index:
                try:
                    value = row['brands']
                    if pd.notna(value):
                        brands = str(value).split(',')
                        if brands:
                            main_brand = brands[0].strip()[:200]
                except (KeyError, AttributeError):
                    pass
            
            # İçerik analizi
            ingredients_text = ''
            if 'ingredients_text' in row.index:
                try:
                    value = row['ingredients_text']
                    if pd.notna(value):
                        ingredients_text = str(value)
                except (KeyError, AttributeError):
                    pass
            
            ingredients_text_length = len(ingredients_text)
            ingredients_word_count = len(ingredients_text.split()) if ingredients_text else 0
            
            # Code değerini güvenli şekilde al
            product_code = 'unknown'
            if 'code' in row.index:
                try:
                    value = row['code']
                    if pd.notna(value):
                        product_code = str(value)
                except (KeyError, AttributeError):
                    pass
            
            return {
                'product_code': product_code,
                'product_name': str(row['product_name'])[:500],
                'main_category': main_category[:200],
                'main_brand': main_brand,
                'main_country': None,  # Bu bilgi preprocessor'da yok
                
                'nutrition_vector': nutrition_vector,
                'allergen_vector': allergen_vector,
                'additives_info': additives_info,
                'nutriscore_data': nutriscore_data,
                'health_indicators': health_indicators,
                'macro_ratios': macro_ratios,
                
                'processing_level': processing_level,
                'nutrition_quality_score': nutrition_quality_score,
                'health_score': health_score,
                
                'ingredients_text': ingredients_text[:2000],
                'ingredients_text_length': ingredients_text_length,
                'ingredients_word_count': ingredients_word_count,
                
                'data_completeness_score': data_completeness,
                'is_valid_for_analysis': data_completeness >= 0.5
            }
            
        except Exception as e:
            logger.error(f"Feature extraction hatası: {str(e)}")
            return None