# backend/aimodels/alternative_engine.py
from typing import List, Dict, Any, Optional, Tuple
import logging
import requests
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)

@dataclass
class AlternativeProduct:
    """Alternatif ürün bilgisi"""
    name: str
    barcode: str
    nutriscore: str
    health_score: int
    reason: str
    nutrients: Dict[str, Any]
    image_url: Optional[str] = None
    brands: Optional[str] = None
    improvements: List[str] = None
    price_comparison: Optional[str] = None
    availability_score: int = 100

class AlternativeEngine:
    """Geliştirilmiş alternatif ürün önerisi motoru"""
    
    def __init__(self):
        self.openfoodfacts_base_url = "https://world.openfoodfacts.org"
        # Kategori eşleştirme tablosu
        self.category_mappings = {
            'beverages': ['sodas', 'fruit-juices', 'teas', 'coffees'],
            'dairy': ['milks', 'yogurts', 'cheeses'],
            'snacks': ['biscuits', 'chips', 'crackers'],
            'breakfast': ['cereals', 'breads', 'jams'],
            'meat-alternatives': ['plant-based-meat', 'tofu', 'seitan']
        }
    
    def find_alternatives(self, product_data: Dict[str, Any], 
                         user_profile: Dict[str, Any],
                         nutritional_analysis: Dict[str, Any],
                         max_alternatives: int = 5) -> List[Dict[str, Any]]:
        """
        Ana alternatif bulma fonksiyonu
        """
        try:
            alternatives = []
            
            # 1. Kategori bazlı alternatifler
            category_alternatives = self._find_category_alternatives(
                product_data, user_profile, nutritional_analysis
            )
            alternatives.extend(category_alternatives)
            
            # 2. Marka bazlı alternatifler
            brand_alternatives = self._find_brand_alternatives(
                product_data, user_profile, nutritional_analysis
            )
            alternatives.extend(brand_alternatives)
            
            # 3. Özel diyet alternatifler (vegan, glutensiz vb.)
            diet_alternatives = self._find_dietary_alternatives(
                product_data, user_profile, nutritional_analysis
            )
            alternatives.extend(diet_alternatives)
            
            # 4. Sağlik durumu bazlı alternatifler
            health_alternatives = self._find_health_based_alternatives(
                product_data, user_profile, nutritional_analysis
            )
            alternatives.extend(health_alternatives)
            
            # Alternatifleri skorla ve sırala
            scored_alternatives = self._score_and_rank_alternatives(
                alternatives, product_data, user_profile, nutritional_analysis
            )
            
            # Dublicate'leri temizle
            unique_alternatives = self._remove_duplicates(scored_alternatives)
            
            return unique_alternatives[:max_alternatives]
            
        except Exception as e:
            logger.error(f"Alternatif bulma hatası: {str(e)}")
            return []
    
    def _find_category_alternatives(self, product_data: Dict, user_profile: Dict, 
                                   nutritional_analysis: Dict) -> List[Dict]:
        """Kategori bazlı alternatif arama"""
        alternatives = []
        
        try:
            # Ürün kategorilerini al
            categories = product_data.get('categories_tags', [])
            if not categories:
                return alternatives
            
            # Ana kategoriyi belirle
            main_category = self._determine_main_category(categories)
            if not main_category:
                return alternatives
            
            # Aynı kategoriden daha sağlıklı ürünler ara
            search_results = self._search_by_category(
                main_category, user_profile, limit=15
            )
            
            # Sonuçları değerlendir
            for result in search_results:
                alternative = self._evaluate_product_as_alternative(
                    result, product_data, user_profile, nutritional_analysis, 'category'
                )
                if alternative:
                    alternatives.append(alternative)
            
            return alternatives
            
        except Exception as e:
            logger.error(f"Kategori alternatif arama hatası: {str(e)}")
            return []
    
    def _find_brand_alternatives(self, product_data: Dict, user_profile: Dict,
                                nutritional_analysis: Dict) -> List[Dict]:
        """Aynı markadan daha sağlıklı alternatifler"""
        alternatives = []
        
        try:
            brands = product_data.get('brands', '')
            if not brands:
                return alternatives
            
            # İlk markayı al
            primary_brand = brands.split(',')[0].strip()
            
            # Aynı markadan ürünler ara
            search_results = self._search_by_brand(primary_brand, limit=10)
            
            for result in search_results:
                # Aynı ürünü atla
                if result.get('code') == product_data.get('code'):
                    continue
                    
                alternative = self._evaluate_product_as_alternative(
                    result, product_data, user_profile, nutritional_analysis, 'brand'
                )
                if alternative:
                    alternatives.append(alternative)
            
            return alternatives
            
        except Exception as e:
            logger.error(f"Marka alternatif arama hatası: {str(e)}")
            return []
    
    def _find_dietary_alternatives(self, product_data: Dict, user_profile: Dict,
                                  nutritional_analysis: Dict) -> List[Dict]:
        """Diyet tercihlerine göre alternatifler"""
        alternatives = []
        dietary_preferences = user_profile.get('dietary_preferences', [])
        
        if not dietary_preferences:
            return alternatives
        
        try:
            categories = product_data.get('categories_tags', [])
            main_category = self._determine_main_category(categories)
            
            for preference in dietary_preferences:
                if preference in ['vegan', 'vegetarian', 'gluten-free', 'organic']:
                    search_results = self._search_by_dietary_preference(
                        main_category, preference, limit=10
                    )
                    
                    for result in search_results:
                        alternative = self._evaluate_product_as_alternative(
                            result, product_data, user_profile, nutritional_analysis, 'dietary'
                        )
                        if alternative:
                            alternatives.append(alternative)
            
            return alternatives
            
        except Exception as e:
            logger.error(f"Diyet alternatif arama hatası: {str(e)}")
            return []
    
    def _find_health_based_alternatives(self, product_data: Dict, user_profile: Dict,
                                       nutritional_analysis: Dict) -> List[Dict]:
        """Sağlık durumuna göre alternatifler"""
        alternatives = []
        health_conditions = user_profile.get('health_conditions', [])
        
        if not health_conditions:
            return alternatives
        
        try:
            categories = product_data.get('categories_tags', [])
            main_category = self._determine_main_category(categories)
            
            # Sağlık durumuna göre özel arama kriterleri
            search_criteria = self._get_health_search_criteria(health_conditions)
            
            if search_criteria:
                search_results = self._search_with_health_criteria(
                    main_category, search_criteria, limit=10
                )
                
                for result in search_results:
                    alternative = self._evaluate_product_as_alternative(
                        result, product_data, user_profile, nutritional_analysis, 'health'
                    )
                    if alternative:
                        alternatives.append(alternative)
            
            return alternatives
            
        except Exception as e:
            logger.error(f"Sağlık bazlı alternatif arama hatası: {str(e)}")
            return []
    
    def _search_by_category(self, category: str, user_profile: Dict, limit: int = 15) -> List[Dict]:
        """Kategoriye göre arama"""
        try:
            params = {
                'tagtype_0': 'categories',
                'tag_contains_0': 'contains',
                'tag_0': category,
                'sort_by': 'nutriscore_score',
                'page_size': limit,
                'json': 1,
                'fields': 'product_name,nutriscore_grade,nova_group,nutriments,brands,image_url,code,categories_tags,labels_tags'
            }
            
            # Kullanıcı tercihlerine göre ek filtreler
            dietary_prefs = user_profile.get('dietary_preferences', [])
            if 'vegan' in dietary_prefs:
                params['tagtype_1'] = 'labels'
                params['tag_contains_1'] = 'contains'
                params['tag_1'] = 'en:vegan'
            elif 'vegetarian' in dietary_prefs:
                params['tagtype_1'] = 'labels'
                params['tag_contains_1'] = 'contains'
                params['tag_1'] = 'en:vegetarian'
            
            response = requests.get(
                f"{self.openfoodfacts_base_url}/cgi/search.pl",
                params=params,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('products', [])
            
            return []
            
        except Exception as e:
            logger.error(f"Kategori arama hatası: {str(e)}")
            return []
    
    def _search_by_brand(self, brand: str, limit: int = 10) -> List[Dict]:
        """Markaya göre arama"""
        try:
            params = {
                'tagtype_0': 'brands',
                'tag_contains_0': 'contains',
                'tag_0': brand,
                'sort_by': 'nutriscore_score',
                'page_size': limit,
                'json': 1,
                'fields': 'product_name,nutriscore_grade,nova_group,nutriments,brands,image_url,code'
            }
            
            response = requests.get(
                f"{self.openfoodfacts_base_url}/cgi/search.pl",
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('products', [])
            
            return []
            
        except Exception as e:
            logger.error(f"Marka arama hatası: {str(e)}")
            return []
    
    def _search_by_dietary_preference(self, category: str, preference: str, limit: int = 10) -> List[Dict]:
        """Diyet tercihine göre arama"""
        try:
            params = {
                'tagtype_0': 'categories',
                'tag_contains_0': 'contains',
                'tag_0': category,
                'tagtype_1': 'labels',
                'tag_contains_1': 'contains',
                'tag_1': f'en:{preference}',
                'sort_by': 'nutriscore_score',
                'page_size': limit,
                'json': 1,
                'fields': 'product_name,nutriscore_grade,nova_group,nutriments,brands,image_url,code,labels_tags'
            }
            
            response = requests.get(
                f"{self.openfoodfacts_base_url}/cgi/search.pl",
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('products', [])
            
            return []
            
        except Exception as e:
            logger.error(f"Diyet tercihi arama hatası: {str(e)}")
            return []
    
    def _evaluate_product_as_alternative(self, candidate: Dict, original: Dict,
                                        user_profile: Dict, original_nutrition: Dict,
                                        source_type: str) -> Optional[Dict]:
        """Ürünü alternatif olarak değerlendir"""
        try:
            # Aynı ürünse atla
            if candidate.get('code') == original.get('code'):
                return None
            
            candidate_nutrients = candidate.get('nutriments', {})
            original_nutrients = original_nutrition.get('values', {})
            
            improvements = []
            health_score = 50  # Başlangıç skoru
            
            # Nutriscore karşılaştırması
            orig_nutriscore = original.get('nutriscore_grade', 'Z').upper()
            cand_nutriscore = candidate.get('nutriscore_grade', 'Z').upper()
            
            nutriscore_values = {'A': 5, 'B': 4, 'C': 3, 'D': 2, 'E': 1, 'Z': 0}
            if nutriscore_values.get(cand_nutriscore, 0) > nutriscore_values.get(orig_nutriscore, 0):
                improvements.append("Daha iyi Nutriscore")
                health_score += 15
            
            # NOVA grubu karşılaştırması
            orig_nova = original.get('nova_group', 4)
            cand_nova = candidate.get('nova_group', 4)
            if cand_nova < orig_nova:
                improvements.append("Daha az işlenmiş")
                health_score += 10
            
            # Beslenme değerleri karşılaştırması
            nutrition_improvements = self._compare_nutrition_values(
                candidate_nutrients, original_nutrients
            )
            improvements.extend(nutrition_improvements['improvements'])
            health_score += nutrition_improvements['score_bonus']
            
            # Kullanıcı profili uyumluluğu
            profile_bonus = self._calculate_profile_compatibility(candidate, user_profile)
            health_score += profile_bonus
            
            # En az bir iyileşme olmalı
            if not improvements or health_score <= 50:
                return None
            
            # Alternatif ürün bilgilerini oluştur
            alternative = {
                'name': candidate.get('product_name', 'Bilinmeyen Ürün'),
                'barcode': candidate.get('code', ''),
                'nutriscore': cand_nutriscore,
                'health_score': min(100, health_score),
                'improvements': improvements,
                'reason': f"Bu ürün şu açılardan daha sağlıklı: {', '.join(improvements[:3])}",
                'brands': candidate.get('brands', ''),
                'image_url': candidate.get('image_url', ''),
                'source_type': source_type,
                'nutrients': self._extract_key_nutrients(candidate_nutrients),
                'labels': candidate.get('labels_tags', [])
            }
            
            return alternative
            
        except Exception as e:
            logger.error(f"Alternatif değerlendirme hatası: {str(e)}")
            return None
    
    def _compare_nutrition_values(self, candidate_nutrients: Dict, 
                                 original_nutrients: Dict) -> Dict[str, Any]:
        """Beslenme değerlerini karşılaştır"""
        improvements = []
        score_bonus = 0
        
        # Şeker karşılaştırması
        orig_sugar = original_nutrients.get('sugars', 0)
        cand_sugar = candidate_nutrients.get('sugars_100g', 0)
        if orig_sugar > 0 and cand_sugar < orig_sugar * 0.8:
            improvements.append(f"%{int((1 - cand_sugar/orig_sugar) * 100)} daha az şeker")
            score_bonus += 10
        
        # Tuz karşılaştırması
        orig_salt = original_nutrients.get('salt', 0)
        cand_salt = candidate_nutrients.get('salt_100g', 0)
        if orig_salt > 0 and cand_salt < orig_salt * 0.8:
            improvements.append(f"%{int((1 - cand_salt/orig_salt) * 100)} daha az tuz")
            score_bonus += 10
        
        # Doymuş yağ karşılaştırması
        orig_sat_fat = original_nutrients.get('saturated_fat', 0)
        cand_sat_fat = candidate_nutrients.get('saturated-fat_100g', 0)
        if orig_sat_fat > 0 and cand_sat_fat < orig_sat_fat * 0.8:
            improvements.append("Daha az doymuş yağ")
            score_bonus += 8
        
        # Kalori karşılaştırması
        orig_calories = original_nutrients.get('energy_kcal', 0)
        cand_calories = candidate_nutrients.get('energy-kcal_100g', 0)
        if orig_calories > 0 and cand_calories < orig_calories * 0.9:
            improvements.append("Daha az kalori")
            score_bonus += 5
        
        # Lif karşılaştırması (yüksek olması iyi)
        orig_fiber = original_nutrients.get('fiber', 0)
        cand_fiber = candidate_nutrients.get('fiber_100g', 0)
        if cand_fiber > orig_fiber * 1.2:
            improvements.append("Daha fazla lif")
            score_bonus += 8
        
        # Protein karşılaştırması (yüksek olması iyi)
        orig_protein = original_nutrients.get('proteins', 0)
        cand_protein = candidate_nutrients.get('proteins_100g', 0)
        if cand_protein > orig_protein * 1.2:
            improvements.append("Daha fazla protein")
            score_bonus += 5
        
        return {
            'improvements': improvements,
            'score_bonus': score_bonus
        }
    
    def _calculate_profile_compatibility(self, candidate: Dict, user_profile: Dict) -> int:
        """Kullanıcı profili ile uyumluluk skoru"""
        bonus = 0
        
        # Diyet tercihleri
        dietary_prefs = user_profile.get('dietary_preferences', [])
        labels = candidate.get('labels_tags', [])
        
        for pref in dietary_prefs:
            if f'en:{pref}' in labels:
                bonus += 10
        
        # Sağlık durumları için bonus
        health_conditions = user_profile.get('health_conditions', [])
        nutrients = candidate.get('nutriments', {})
        
        if 'diabetes_type_1' in health_conditions or 'diabetes_type_2' in health_conditions:
            sugar = nutrients.get('sugars_100g', 0)
            if sugar < 5:  # Düşük şeker
                bonus += 15
        
        if 'hypertension' in health_conditions:
            salt = nutrients.get('salt_100g', 0)
            if salt < 0.5:  # Düşük tuz
                bonus += 15
        
        if 'high_cholesterol' in health_conditions:
            sat_fat = nutrients.get('saturated-fat_100g', 0)
            if sat_fat < 3:  # Düşük doymuş yağ
                bonus += 15
        
        return bonus
    
    def _score_and_rank_alternatives(self, alternatives: List[Dict], product_data: Dict,
                                    user_profile: Dict, nutritional_analysis: Dict) -> List[Dict]:
        """Alternatifleri skorla ve sırala"""
        if not alternatives:
            return []
        
        # Her alternatif için toplam skor hesapla
        for alt in alternatives:
            total_score = alt.get('health_score', 0)
            
            # Source type bonusu
            source_bonus = {
                'category': 5,
                'brand': 3,
                'dietary': 8,
                'health': 10
            }
            total_score += source_bonus.get(alt.get('source_type', ''), 0)
            
            # İyileştirme sayısı bonusu
            improvements_count = len(alt.get('improvements', []))
            total_score += improvements_count * 2
            
            alt['total_score'] = total_score
        
        # Skora göre sırala (yüksekten düşüğe)
        return sorted(alternatives, key=lambda x: x.get('total_score', 0), reverse=True)
    
    def _remove_duplicates(self, alternatives: List[Dict]) -> List[Dict]:
        """Dublicate alternatifleri temizle"""
        seen_barcodes = set()
        unique_alternatives = []
        
        for alt in alternatives:
            barcode = alt.get('barcode', '')
            if barcode and barcode not in seen_barcodes:
                seen_barcodes.add(barcode)
                unique_alternatives.append(alt)
            elif not barcode:  # Barcode yoksa isimle kontrol et
                name = alt.get('name', '').lower()
                if name not in [a.get('name', '').lower() for a in unique_alternatives]:
                    unique_alternatives.append(alt)
        
        return unique_alternatives
    
    def _determine_main_category(self, categories: List[str]) -> str:
        """Ana kategoriyi belirle"""
        if not categories:
            return ""
        
        # İlk kategoriyi al ve temizle
        main_cat = categories[0].replace('en:', '').replace('fr:', '')
        return main_cat
    
    def _get_health_search_criteria(self, health_conditions: List[str]) -> Dict[str, Any]:
        """Sağlık durumuna göre arama kriterleri"""
        criteria = {}
        
        if any(condition in ['diabetes_type_1', 'diabetes_type_2', 'prediabetes'] 
               for condition in health_conditions):
            criteria['max_sugar'] = 10  # Max 10g şeker
            criteria['prefer_labels'] = ['no-added-sugar', 'sugar-free']
        
        if 'hypertension' in health_conditions:
            criteria['max_salt'] = 0.8  # Max 0.8g tuz
            criteria['prefer_labels'] = ['low-sodium', 'no-salt-added']
        
        if 'high_cholesterol' in health_conditions:
            criteria['max_saturated_fat'] = 3  # Max 3g doymuş yağ
            criteria['prefer_labels'] = ['low-fat', 'cholesterol-free']
        
        return criteria
    
    def _search_with_health_criteria(self, category: str, criteria: Dict, limit: int = 10) -> List[Dict]:
        """Sağlık kriterlerine göre arama"""
        # Bu fonksiyon OpenFoodFacts API'den sağlık kriterlerine uygun ürünleri arar
        # Şimdilik basit bir kategori araması yapıyoruz
        return self._search_by_category(category, {}, limit)
    
    def _extract_key_nutrients(self, nutrients: Dict) -> Dict[str, float]:
        """Anahtar besin değerlerini çıkar"""
        return {
            'energy_kcal': nutrients.get('energy-kcal_100g', 0),
            'sugars': nutrients.get('sugars_100g', 0),
            'salt': nutrients.get('salt_100g', 0),
            'fat': nutrients.get('fat_100g', 0),
            'saturated_fat': nutrients.get('saturated-fat_100g', 0),
            'proteins': nutrients.get('proteins_100g', 0),
            'fiber': nutrients.get('fiber_100g', 0)
        }