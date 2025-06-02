# backend/aimodels/allergy_warnings.py
from typing import List, Dict, Any
import re
import logging

logger = logging.getLogger(__name__)

class AllergyAnalyzer:
    """Alerji uyarıları analiz sınıfı"""
    
    def __init__(self):
        # Allerjen eşleşme tablosu - OpenFoodFacts verileri için
        self.allergen_mapping = {
            'peanuts': {
                'keywords': ['peanut', 'groundnut', 'arachis', 'yer fıstığı', 'yer fistigi'],
                'allergen_tags': ['en:peanuts'],
                'ingredient_patterns': [r'\bpeanut\b', r'\bgroundnut\b', r'yer\s*fıstığı'],
                'tr_name': 'Yer fıstığı'
            },
            'tree_nuts': {
                'keywords': ['almond', 'walnut', 'hazelnut', 'cashew', 'pistachio', 'pecan', 
                           'badem', 'ceviz', 'fındık', 'kaju', 'antep fıstığı'],
                'allergen_tags': ['en:nuts'],
                'ingredient_patterns': [r'\b(almond|walnut|hazelnut|cashew|pistachio|pecan)\b',
                                      r'\b(badem|ceviz|fındık|kaju)\b'],
                'tr_name': 'Sert kabuklu meyveler'
            },
            'milk': {
                'keywords': ['milk', 'dairy', 'lactose', 'casein', 'whey', 'butter', 'cream',
                           'süt', 'laktoz', 'kazein', 'tereyağı', 'krema', 'peynir'],
                'allergen_tags': ['en:milk'],
                'ingredient_patterns': [r'\b(milk|dairy|lactose|casein|whey|butter|cream)\b',
                                      r'\b(süt|laktoz|kazein|tereyağı|krema|peynir)\b'],
                'tr_name': 'Süt ve süt ürünleri'
            },
            'eggs': {
                'keywords': ['egg', 'albumin', 'lecithin', 'yumurta', 'albümin', 'lesitin'],
                'allergen_tags': ['en:eggs'],
                'ingredient_patterns': [r'\b(egg|albumin|lecithin)\b', r'\b(yumurta|albümin|lesitin)\b'],
                'tr_name': 'Yumurta'
            },
            'wheat': {
                'keywords': ['wheat', 'gluten', 'flour', 'bran', 'bulgur', 'semolina',
                           'buğday', 'glüten', 'un', 'kepek', 'bulgur', 'irmik'],
                'allergen_tags': ['en:gluten'],
                'ingredient_patterns': [r'\b(wheat|gluten|flour|bran|bulgur|semolina)\b',
                                      r'\b(buğday|glüten|un|kepek|bulgur|irmik)\b'],
                'tr_name': 'Buğday (Glüten)'
            },
            'soy': {
                'keywords': ['soy', 'soya', 'tofu', 'lecithin', 'soja'],
                'allergen_tags': ['en:soybeans'],
                'ingredient_patterns': [r'\b(soy|soya|tofu|lecithin|soja)\b'],
                'tr_name': 'Soya'
            },
            'fish': {
                'keywords': ['fish', 'salmon', 'tuna', 'cod', 'balık', 'somon', 'ton', 'morina'],
                'allergen_tags': ['en:fish'],
                'ingredient_patterns': [r'\b(fish|salmon|tuna|cod)\b', r'\b(balık|somon|ton|morina)\b'],
                'tr_name': 'Balık'
            },
            'shellfish': {
                'keywords': ['shrimp', 'crab', 'lobster', 'mussel', 'oyster', 'scallop',
                           'karides', 'yengeç', 'ıstakoz', 'midye', 'istiridye'],
                'allergen_tags': ['en:crustaceans', 'en:molluscs'],
                'ingredient_patterns': [r'\b(shrimp|crab|lobster|mussel|oyster|scallop)\b',
                                      r'\b(karides|yengeç|ıstakoz|midye|istiridye)\b'],
                'tr_name': 'Kabuklu deniz ürünleri'
            },
            'sesame': {
                'keywords': ['sesame', 'tahini', 'susam', 'tahin'],
                'allergen_tags': ['en:sesame-seeds'],
                'ingredient_patterns': [r'\b(sesame|tahini)\b', r'\b(susam|tahin)\b'],
                'tr_name': 'Susam'
            },
            'corn': {
                'keywords': ['corn', 'maize', 'cornstarch', 'mısır', 'nişasta'],
                'allergen_tags': [],  # Corn genelde allergen tag'i yok OpenFoodFacts'ta
                'ingredient_patterns': [r'\b(corn|maize|cornstarch)\b', r'\b(mısır|nişasta)\b'],
                'tr_name': 'Mısır'
            }
        }
    
    def analyze(self, product_data: Dict[str, Any], user_allergies: List[str]) -> Dict[str, Any]:
        """
        Ürünü kullanıcının alerjilerine göre analiz et
        
        Args:
            product_data: OpenFoodFacts ürün verisi
            user_allergies: Kullanıcının alerji listesi
            
        Returns:
            Alerji analiz sonucu
        """
        if not user_allergies:
            return {'alerts': [], 'detected_allergens': [], 'is_safe': True}
        
        try:
            detected_allergens = []
            alerts = []
            
            for allergy in user_allergies:
                if allergy not in self.allergen_mapping:
                    logger.warning(f"Bilinmeyen alerji tipi: {allergy}")
                    continue
                
                detection_result = self._detect_allergen(product_data, allergy)
                
                if detection_result['detected']:
                    detected_allergens.append({
                        'allergen': allergy,
                        'tr_name': self.allergen_mapping[allergy]['tr_name'],
                        'detection_method': detection_result['method'],
                        'confidence': detection_result['confidence'],
                        'found_in': detection_result['found_in']
                    })
                    
                    # Uyarı oluştur
                    alert = self._create_allergy_alert(allergy, detection_result)
                    alerts.append(alert)
            
            is_safe = len(detected_allergens) == 0
            
            return {
                'alerts': alerts,
                'detected_allergens': detected_allergens,
                'is_safe': is_safe,
                'checked_allergies': user_allergies,
                'total_detections': len(detected_allergens)
            }
            
        except Exception as e:
            logger.error(f"Alerji analizi hatası: {str(e)}")
            return {
                'error': f'Alerji analizi hatası: {str(e)}',
                'alerts': [],
                'detected_allergens': [],
                'is_safe': False
            }
    
    def _detect_allergen(self, product_data: Dict[str, Any], allergy: str) -> Dict[str, Any]:
        """
        Belirli bir alerjeni üründe tespit et
        """
        allergen_info = self.allergen_mapping[allergy]
        detection_methods = []
        confidence = 0
        found_in = []
        
        # 1. Allergen tags kontrolü (en güvenilir)
        allergen_tags = product_data.get('allergens_tags', [])
        for tag in allergen_info['allergen_tags']:
            if tag in allergen_tags:
                detection_methods.append('allergen_tags')
                confidence = max(confidence, 95)
                found_in.append(f'Allergen Tags: {tag}')
        
        # 2. Ingredients text analizi
        ingredients_text = product_data.get('ingredients_text', '').lower()
        if ingredients_text:
            for pattern in allergen_info['ingredient_patterns']:
                matches = re.findall(pattern, ingredients_text, re.IGNORECASE)
                if matches:
                    detection_methods.append('ingredients_text')
                    confidence = max(confidence, 85)
                    found_in.extend([f'İçerik: {match}' for match in matches])
        
        # 3. Traces kontrolü
        traces = product_data.get('traces_tags', [])
        for tag in allergen_info['allergen_tags']:
            if tag in traces:
                detection_methods.append('traces')
                confidence = max(confidence, 60)  # Traces daha düşük güven
                found_in.append(f'İz miktarda: {tag}')
        
        # 4. Keywords kontrolü (en düşük güven)
        product_name = product_data.get('product_name', '').lower()
        for keyword in allergen_info['keywords']:
            if keyword.lower() in product_name or keyword.lower() in ingredients_text:
                detection_methods.append('keywords')
                confidence = max(confidence, 70)
                found_in.append(f'Anahtar kelime: {keyword}')
        
        return {
            'detected': len(detection_methods) > 0,
            'method': detection_methods,
            'confidence': confidence,
            'found_in': found_in
        }
    
    def _create_allergy_alert(self, allergy: str, detection_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Alerji uyarısı oluştur
        """
        allergen_info = self.allergen_mapping[allergy]
        confidence = detection_result['confidence']
        
        # Ciddiyet seviyesini belirle
        if 'allergen_tags' in detection_result['method']:
            severity = 'critical'
        elif confidence >= 85:
            severity = 'critical'
        elif 'traces' in detection_result['method']:
            severity = 'warning'
        else:
            severity = 'warning'
        
        # Mesaj oluştur
        if severity == 'critical':
            message = f"⚠️ DİKKAT: Bu ürün {allergen_info['tr_name']} içeriyor!"
            action = "Bu ürünü kesinlikle tüketmeyin."
        else:
            message = f"⚠️ UYARI: Bu ürün {allergen_info['tr_name']} içerebilir"
            action = "Dikkatli olun ve etiketi kontrol edin."
        
        return {
            'type': 'allergy',
            'severity': severity,
            'allergen': allergy,
            'allergen_name': allergen_info['tr_name'],
            'message': message,
            'description': f"Tespit yöntemi: {', '.join(detection_result['method'])}",
            'action': action,
            'confidence': confidence,
            'found_in': detection_result['found_in']
        }
    
    def get_critical_allergens(self, product_data: Dict[str, Any], user_allergies: List[str]) -> List[Dict[str, Any]]:
        """
        Sadece kritik alerjen uyarılarını getir (hızlı kontrol için)
        """
        if not user_allergies:
            return []
        
        critical_alerts = []
        
        # Allergen tags'i kontrol et (en hızlı ve güvenilir)
        allergen_tags = product_data.get('allergens_tags', [])
        
        for allergy in user_allergies:
            if allergy in self.allergen_mapping:
                allergen_info = self.allergen_mapping[allergy]
                
                # Sadece allergen tags kontrolü yap (hız için)
                for tag in allergen_info['allergen_tags']:
                    if tag in allergen_tags:
                        critical_alerts.append({
                            'type': 'allergy',
                            'severity': 'critical',
                            'allergen': allergy,
                            'allergen_name': allergen_info['tr_name'],
                            'message': f"⚠️ DİKKAT: Bu ürün {allergen_info['tr_name']} içeriyor!",
                            'action': "Bu ürünü kesinlikle tüketmeyin."
                        })
                        break
        
        return critical_alerts