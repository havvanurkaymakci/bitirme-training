# backend/aimodels/dietary_warnings.py
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class DietaryAnalyzer:
    """Diyet tercihlerine göre uyarı analizi"""
    
    def __init__(self):
        # Diyet kategorileri ve kontrol edilecek bileşenler
        self.dietary_restrictions = {
            'vegan': {
                'forbidden_ingredients': [
                    'et', 'tavuk', 'balık', 'süt', 'peynir', 'yoğurt', 'tereyağı',
                    'yumurta', 'bal', 'jelatin', 'lanolin', 'karmin', 'shellac',
                    'beef', 'chicken', 'fish', 'milk', 'cheese', 'yogurt', 'butter',
                    'egg', 'honey', 'gelatin', 'whey', 'casein', 'lactose'
                ],
                'forbidden_labels': ['en:non-vegan'],
                'required_labels': [],
                'name': 'Vegan'
            },
            'vegetarian': {
                'forbidden_ingredients': [
                    'et', 'tavuk', 'balık', 'jelatin', 'beef', 'chicken', 'fish',
                    'meat', 'gelatin', 'rennet', 'lard', 'tallow'
                ],
                'forbidden_labels': ['en:non-vegetarian'],
                'required_labels': [],
                'name': 'Vejetaryen'
            },
            'pescatarian': {
                'forbidden_ingredients': [
                    'et', 'tavuk', 'beef', 'chicken', 'meat', 'pork', 'lamb'
                ],
                'forbidden_labels': [],
                'required_labels': [],
                'name': 'Pescatarian'
            },
            'gluten_free': {
                'forbidden_ingredients': [
                    'buğday', 'arpa', 'çavdar', 'tritikale', 'gluten',
                    'wheat', 'barley', 'rye', 'oats', 'malt', 'flour',
                    'bread', 'pasta', 'bulgur'
                ],
                'forbidden_labels': ['en:contains-gluten'],
                'required_labels': [],
                'name': 'Glütensiz'
            },
            'lactose_free': {
                'forbidden_ingredients': [
                    'süt', 'laktoz', 'milk', 'lactose', 'dairy', 'cream',
                    'butter', 'cheese', 'yogurt', 'whey', 'casein'
                ],
                'forbidden_labels': ['en:contains-milk'],
                'required_labels': [],
                'name': 'Laktozsuz'
            },
            'ketogenic': {
                'max_carbs': 5,  # 100g başına max 5g karbonhidrat
                'forbidden_ingredients': [
                    'şeker', 'sugar', 'corn syrup', 'maltodextrin',
                    'potato', 'rice', 'wheat', 'oats'
                ],
                'forbidden_labels': [],
                'required_labels': [],
                'name': 'Ketojenik'
            },
            'paleo': {
                'forbidden_ingredients': [
                    'tahıl', 'grain', 'sugar', 'dairy', 'legume', 'bean',
                    'soy', 'peanut', 'corn', 'wheat', 'rice', 'oats'
                ],
                'forbidden_labels': [],
                'required_labels': [],
                'name': 'Paleo'
            },
            'low_carb': {
                'max_carbs': 10,  # 100g başına max 10g karbonhidrat
                'forbidden_ingredients': [],
                'forbidden_labels': [],
                'required_labels': [],
                'name': 'Düşük Karbonhidrat'
            },
            'high_protein': {
                'min_protein': 15,  # 100g başına min 15g protein
                'forbidden_ingredients': [],
                'forbidden_labels': [],
                'required_labels': [],
                'name': 'Yüksek Protein'
            },
            'low_fat': {
                'max_fat': 3,  # 100g başına max 3g yağ
                'forbidden_ingredients': [],
                'forbidden_labels': [],
                'required_labels': [],
                'name': 'Düşük Yağ'
            },
            'low_sodium': {
                'max_sodium': 0.3,  # 100g başına max 0.3g sodyum
                'forbidden_ingredients': [],
                'forbidden_labels': [],
                'required_labels': [],
                'name': 'Düşük Sodyum'
            },
            'halal': {
                'forbidden_ingredients': [
                    'pork', 'domuz', 'alcohol', 'alkol', 'wine', 'beer',
                    'gelatin', 'lard', 'bacon', 'ham'
                ],
                'forbidden_labels': ['en:non-halal'],
                'required_labels': [],
                'name': 'Helal'
            },
            'kosher': {
                'forbidden_ingredients': [
                    'pork', 'domuz', 'shellfish', 'karides', 'mixing meat and dairy'
                ],
                'forbidden_labels': ['en:non-kosher'],
                'required_labels': [],
                'name': 'Koşer'
            }
        }
    
    def analyze(self, product_data: Dict[str, Any], user_dietary_preferences: List[str]) -> Dict[str, Any]:
        """
        Ürünü kullanıcının diyet tercihlerine göre analiz et
        """
        try:
            alerts = []
            compliance = {}
            
            for preference in user_dietary_preferences:
                if preference in self.dietary_restrictions:
                    restriction = self.dietary_restrictions[preference]
                    analysis_result = self._check_dietary_compliance(product_data, restriction, preference)
                    
                    compliance[preference] = analysis_result['compliant']
                    
                    if not analysis_result['compliant']:
                        alerts.append({
                            'type': 'dietary_violation',
                            'preference': preference,
                            'preference_name': restriction['name'],
                            'severity': 'warning',
                            'message': analysis_result['message'],
                            'details': analysis_result['violations'],
                            'icon': '🚫'
                        })
            
            return {
                'alerts': alerts,
                'compliance': compliance,
                'total_violations': len(alerts),
                'is_compliant': len(alerts) == 0
            }
            
        except Exception as e:
            logger.error(f"Diyet analizi hatası: {str(e)}")
            return {
                'alerts': [{
                    'type': 'analysis_error',
                    'severity': 'info',
                    'message': f'Diyet analizi yapılamadı: {str(e)}',
                    'icon': '⚠️'
                }],
                'compliance': {},
                'total_violations': 0,
                'is_compliant': False
            }
    
    def get_critical_warnings(self, product_data: Dict[str, Any], user_dietary_preferences: List[str]) -> Dict[str, Any]:
        """Sadece kritik diyet uyarılarını al (hızlı analiz için)"""
        alerts = []
        
        for preference in user_dietary_preferences:
            if preference in ['vegan', 'vegetarian', 'gluten_free', 'lactose_free', 'halal', 'kosher']:
                restriction = self.dietary_restrictions[preference]
                if not self._quick_compliance_check(product_data, restriction):
                    alerts.append({
                        'type': 'critical_dietary_violation',
                        'preference': preference,
                        'preference_name': restriction['name'],
                        'severity': 'critical',
                        'message': f'Bu ürün {restriction["name"]} diyetine uygun değil!',
                        'icon': '🚫'
                    })
        
        return {'alerts': alerts}
    
    def _check_dietary_compliance(self, product_data: Dict[str, Any], restriction: Dict, preference: str) -> Dict[str, Any]:
        """Belirli bir diyet kısıtlamasına uygunluğu kontrol et"""
        violations = []
        
        # İçerik kontrolü
        ingredients_text = product_data.get('ingredients_text', '').lower()
        if ingredients_text:
            for forbidden in restriction.get('forbidden_ingredients', []):
                if forbidden.lower() in ingredients_text:
                    violations.append(f"İçeriğinde {forbidden} bulunuyor")
        
        # Etiket kontrolü
        labels = product_data.get('labels_tags', [])
        for forbidden_label in restriction.get('forbidden_labels', []):
            if forbidden_label in labels:
                violations.append(f"Uygun olmayan etiket: {forbidden_label}")
        
        # Beslenme değeri kontrolleri
        nutriments = product_data.get('nutriments', {})
        
        # Karbonhidrat kontrolü
        if 'max_carbs' in restriction:
            carbs = nutriments.get('carbohydrates_100g', 0)
            if carbs > restriction['max_carbs']:
                violations.append(f"Çok yüksek karbonhidrat: {carbs}g (max {restriction['max_carbs']}g)")
        
        # Protein kontrolü
        if 'min_protein' in restriction:
            protein = nutriments.get('proteins_100g', 0)
            if protein < restriction['min_protein']:
                violations.append(f"Yetersiz protein: {protein}g (min {restriction['min_protein']}g)")
        
        # Yağ kontrolü
        if 'max_fat' in restriction:
            fat = nutriments.get('fat_100g', 0)
            if fat > restriction['max_fat']:
                violations.append(f"Çok yüksek yağ: {fat}g (max {restriction['max_fat']}g)")
        
        # Sodyum kontrolü
        if 'max_sodium' in restriction:
            sodium = nutriments.get('sodium_100g', 0)
            if sodium > restriction['max_sodium']:
                violations.append(f"Çok yüksek sodyum: {sodium}g (max {restriction['max_sodium']}g)")
        
        is_compliant = len(violations) == 0
        
        if not is_compliant:
            message = f"{restriction['name']} diyetine uygun değil"
        else:
            message = f"{restriction['name']} diyetine uygun"
        
        return {
            'compliant': is_compliant,
            'message': message,
            'violations': violations
        }
    
    def _quick_compliance_check(self, product_data: Dict[str, Any], restriction: Dict) -> bool:
        """Hızlı uygunluk kontrolü (sadece kritik kontroller)"""
        ingredients_text = product_data.get('ingredients_text', '').lower()
        
        # Yasak içerikleri kontrol et
        for forbidden in restriction.get('forbidden_ingredients', []):
            if forbidden.lower() in ingredients_text:
                return False
        
        # Yasak etiketleri kontrol et
        labels = product_data.get('labels_tags', [])
        for forbidden_label in restriction.get('forbidden_labels', []):
            if forbidden_label in labels:
                return False
        
        return True
    
    def get_dietary_suggestions(self, product_data: Dict[str, Any], user_dietary_preferences: List[str]) -> List[Dict[str, Any]]:
        """Diyet tercihlerine göre öneriler"""
        suggestions = []
        
        for preference in user_dietary_preferences:
            if preference == 'ketogenic':
                nutriments = product_data.get('nutriments', {})
                carbs = nutriments.get('carbohydrates_100g', 0)
                if carbs > 5:
                    suggestions.append({
                        'type': 'portion_control',
                        'message': f'Ketojenik diyet için porsiyon kontrolü yapın. Karbonhidrat oranı yüksek ({carbs}g)',
                        'recommendation': 'Daha küçük porsiyonlar tüketin veya alternatif arayın'
                    })
            
            elif preference == 'low_sodium':
                nutriments = product_data.get('nutriments', {})
                sodium = nutriments.get('sodium_100g', 0)
                if sodium > 0.3:
                    suggestions.append({
                        'type': 'sodium_warning',
                        'message': f'Sodyum oranı yüksek ({sodium}g)',
                        'recommendation': 'Düşük sodyumlu alternatifler arayın'
                    })
        
        return suggestions