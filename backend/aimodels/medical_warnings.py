# backend/aimodels/medical_warnings.py
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class MedicalAnalyzer:
    """Tıbbi durumlar için ürün analizi"""
    
    def __init__(self):
        # Tıbbi durumlara göre beslenme kısıtlamaları ve öneriler
        self.medical_restrictions = {
            # Metabolik/Endokrin Durumlar
            'diabetes_type_1': {
                'max_sugars': 5,
                'max_carbs': 15,
                'monitor_gi': True,
                'avoid_ingredients': ['high fructose corn syrup', 'glucose syrup', 'sucrose'],
                'warnings': {
                    'high_sugar': 'Tip 1 diyabet için yüksek şeker içeriği tehlikeli olabilir',
                    'high_carbs': 'Karbonhidrat miktarı insulin dozajını etkileyebilir'
                }
            },
            'diabetes_type_2': {
                'max_sugars': 8,
                'max_carbs': 20,
                'max_saturated_fat': 5,
                'monitor_calories': True,
                'avoid_ingredients': ['high fructose corn syrup', 'glucose syrup'],
                'warnings': {
                    'high_sugar': 'Kan şekeri kontrolü için şeker miktarına dikkat edin',
                    'high_carbs': 'Karbonhidrat sayımı önemli',
                    'high_calories': 'Kilo kontrolü için kaloriyi takip edin'
                }
            },
            'prediabetes': {
                'max_sugars': 10,
                'max_carbs': 25,
                'monitor_gi': True,
                'warnings': {
                    'high_sugar': 'Prediabetes riski için şeker kısıtlaması önemli',
                    'high_gi': 'Yüksek glisemik indeksli yiyeceklerden kaçının'
                }
            },
            'insulin_resistance': {
                'max_sugars': 8,
                'max_carbs': 20,
                'max_saturated_fat': 5,
                'monitor_gi': True,
                'warnings': {
                    'high_sugar': 'İnsülin direnci için şeker kısıtlaması kritik',
                    'high_refined_carbs': 'Rafine karbonhidratlar direnci artırabilir'
                }
            },
            'hypoglycemia': {
                'min_carbs': 15,
                'avoid_artificial_sweeteners': True,
                'warnings': {
                    'very_low_carbs': 'Çok düşük karbonhidrat hipoglisemi riskini artırabilir',
                    'artificial_sweeteners': 'Yapay tatlandırıcılar kan şekeri dengesini bozabilir'
                }
            },
            'hypothyroidism': {
                'avoid_ingredients': ['soy', 'cabbage', 'broccoli', 'cauliflower'],
                'limit_fiber': 25,
                'warnings': {
                    'high_soy': 'Soya tiroid ilaç emilimini etkileyebilir',
                    'goitrogenic_foods': 'Brokoli, karnabahar gibi goitrojenik yiyecekler sınırlı tüketilmeli'
                }
            },
            'hyperthyroidism': {
                'avoid_ingredients': ['iodine', 'kelp', 'seaweed'],
                'limit_caffeine': True,
                'warnings': {
                    'high_iodine': 'Yüksek iyot hipertiroidi belirtilerini kötüleştirebilir',
                    'caffeine': 'Kafein çarpıntı ve tremoru artırabilir'
                }
            },
            'pcos': {
                'max_sugars': 8,
                'max_carbs': 20,
                'limit_dairy': True,
                'warnings': {
                    'high_sugar': 'PCOS için insulin direnci riski',
                    'dairy': 'Süt ürünleri hormon dengesini etkileyebilir'
                }
            },
            
            # Kardiyovasküler Durumlar
            'hypertension': {
                'max_sodium': 600,  # mg per 100g
                'max_salt': 1.5,    # g per 100g
                'avoid_ingredients': ['monosodium glutamate', 'sodium nitrite'],
                'warnings': {
                    'high_sodium': 'Yüksek tansiyonlu hastalarda sodyum kısıtlaması kritik',
                    'hidden_salt': 'Gizli tuz kaynakları tansiyonu yükseltebilir'
                }
            },
            'high_cholesterol': {
                'max_saturated_fat': 3,
                'max_trans_fat': 0.2,
                'max_cholesterol': 50,
                'avoid_ingredients': ['palm oil', 'coconut oil', 'hydrogenated oil'],
                'warnings': {
                    'high_saturated_fat': 'Doymuş yağ kolesterolü yükseltir',
                    'trans_fat': 'Trans yağlar kalp hastalığı riskini artırır'
                }
            },
            'heart_disease': {
                'max_sodium': 500,
                'max_saturated_fat': 2,
                'max_trans_fat': 0,
                'avoid_ingredients': ['hydrogenated oil', 'partially hydrogenated oil'],
                'warnings': {
                    'high_sodium': 'Kalp hastalığında sodyum kısıtlaması hayati',
                    'harmful_fats': 'Zararlı yağlar mevcut durumu kötüleştirebilir'
                }
            },
            
            # Gastrointestinal Durumlar
            'celiac_disease': {
                'avoid_ingredients': ['wheat', 'barley', 'rye', 'oats', 'gluten'],
                'check_cross_contamination': True,
                'warnings': {
                    'gluten_present': 'Çölyak hastası için gluten kesinlikle yasak',
                    'cross_contamination': 'Çapraz bulaşma riski kontrol edilmeli'
                }
            },
            'irritable_bowel_syndrome': {
                'limit_fiber': 10,
                'avoid_ingredients': ['fructose', 'lactose', 'sorbitol', 'mannitol'],
                'fodmap_check': True,
                'warnings': {
                    'high_fiber': 'Yüksek lif IBS belirtilerini tetikleyebilir',
                    'fodmap_foods': 'FODMAP içeren yiyecekler semptomları artırabilir'
                }
            },
            'inflammatory_bowel_disease': {
                'limit_fiber': 8,
                'avoid_ingredients': ['nuts', 'seeds', 'corn', 'popcorn'],
                'warnings': {
                    'high_fiber': 'IBD alevlenmelerinde lif kısıtlaması gerekli',
                    'irritating_foods': 'Fındık, tohum gibi yiyecekler irritasyona neden olabilir'
                }
            },
            'acid_reflux': {
                'avoid_ingredients': ['citric acid', 'tomato', 'garlic', 'onion'],
                'limit_fat': 15,
                'avoid_spicy': True,
                'warnings': {
                    'acidic_foods': 'Asitli yiyecekler reflüyü tetikleyebilir',
                    'high_fat': 'Yağlı yiyecekler mide boşalmasını yavaşlatır'
                }
            },
            'lactose_intolerance': {
                'avoid_ingredients': ['milk', 'lactose', 'whey', 'casein'],
                'warnings': {
                    'lactose_present': 'Laktoz intoleransı için süt ürünleri problematik'
                }
            },
            
            # Diğer Durumlar
            'anemia': {
                'monitor_iron_absorption': True,
                'avoid_with_iron': ['tea', 'coffee', 'calcium'],
                'warnings': {
                    'iron_blockers': 'Çay, kahve demir emilimini engeller'
                }
            },
            'osteoporosis': {
                'limit_sodium': 600,
                'limit_caffeine': True,
                'warnings': {
                    'high_sodium': 'Fazla sodyum kalsiyum kaybına neden olur',
                    'caffeine': 'Kafein kalsiyum emilimini azaltabilir'
                }
            },
            'chronic_kidney_disease': {
                'max_sodium': 400,
                'max_potassium': 200,
                'max_phosphorus': 100,
                'limit_protein': 15,
                'warnings': {
                    'high_sodium': 'Böbrek hastalığında sodyum kısıtlaması kritik',
                    'high_potassium': 'Yüksek potasyum tehlikeli olabilir',
                    'high_protein': 'Protein kısıtlaması gerekli olabilir'
                }
            },
            'fatty_liver': {
                'limit_fructose': 5,
                'max_saturated_fat': 5,
                'avoid_alcohol': True,
                'warnings': {
                    'high_fructose': 'Fruktoz karaciğer yağlanmasını artırır',
                    'alcohol': 'Alkol karaciğer hasarını hızlandırır'
                }
            },
            'gout': {
                'limit_purines': True,
                'avoid_ingredients': ['anchovies', 'sardines', 'organ meats'],
                'limit_fructose': 5,
                'warnings': {
                    'high_purine': 'Yüksek pürin gut ataklarını tetikleyebilir',
                    'fructose': 'Fruktoz ürik asit seviyesini yükseltir'
                }
            }
        }
    
    def analyze(self, product_data: Dict[str, Any], medical_conditions: List[str]) -> Dict[str, Any]:
        """
        Tıbbi durumlar için ürün analizi
        
        Args:
            product_data: Ürün verileri
            medical_conditions: Kullanıcının tıbbi durumları
            
        Returns:
            Analiz sonuçları
        """
        if not medical_conditions:
            return {'alerts': [], 'is_safe': True, 'recommendations': []}
        
        alerts = []
        recommendations = []
        is_safe = True
        
        nutriments = product_data.get('nutriments', {})
        ingredients_text = product_data.get('ingredients_text', '').lower()
        ingredients_tags = product_data.get('ingredients_tags', [])
        
        for condition in medical_conditions:
            if condition not in self.medical_restrictions:
                continue
                
            restrictions = self.medical_restrictions[condition]
            condition_alerts = self._check_condition_restrictions(
                condition, restrictions, nutriments, ingredients_text, ingredients_tags
            )
            
            if condition_alerts:
                alerts.extend(condition_alerts)
                # Kritik uyarı varsa güvenli değil
                if any(alert.get('severity') == 'critical' for alert in condition_alerts):
                    is_safe = False
            
            # Öneriler oluştur
            condition_recommendations = self._generate_medical_recommendations(
                condition, restrictions, nutriments
            )
            recommendations.extend(condition_recommendations)
        
        return {
            'alerts': alerts,
            'is_safe': is_safe,
            'recommendations': recommendations,
            'medical_score': self._calculate_medical_score(alerts)
        }
    
    def get_critical_warnings(self, product_data: Dict[str, Any], medical_conditions: List[str]) -> Dict[str, Any]:
        """Sadece kritik uyarıları getir (hızlı analiz için)"""
        if not medical_conditions:
            return {'alerts': []}
        
        alerts = []
        nutriments = product_data.get('nutriments', {})
        ingredients_text = product_data.get('ingredients_text', '').lower()
        
        for condition in medical_conditions:
            if condition not in self.medical_restrictions:
                continue
                
            restrictions = self.medical_restrictions[condition]
            critical_alerts = self._check_critical_restrictions(
                condition, restrictions, nutriments, ingredients_text
            )
            alerts.extend(critical_alerts)
        
        return {'alerts': alerts}
    
    def _check_condition_restrictions(self, condition: str, restrictions: Dict, 
                                   nutriments: Dict, ingredients_text: str, 
                                   ingredients_tags: List[str]) -> List[Dict[str, Any]]:
        """Belirli bir tıbbi durum için kısıtlamaları kontrol et"""
        alerts = []
        
        # Şeker kontrolü
        if 'max_sugars' in restrictions:
            sugars = nutriments.get('sugars_100g', 0)
            if sugars > restrictions['max_sugars']:
                alerts.append({
                    'type': 'medical_warning',
                    'condition': condition,
                    'severity': 'critical' if sugars > restrictions['max_sugars'] * 2 else 'warning',
                    'message': restrictions['warnings'].get('high_sugar', 'Yüksek şeker içeriği'),
                    'details': f"Şeker: {sugars}g/100g (Önerilen: max {restrictions['max_sugars']}g)",
                    'turkish_title': 'Yüksek Şeker Uyarısı'
                })
        
        # Karbonhidrat kontrolü
        if 'max_carbs' in restrictions:
            carbs = nutriments.get('carbohydrates_100g', 0)
            if carbs > restrictions['max_carbs']:
                alerts.append({
                    'type': 'medical_warning',
                    'condition': condition,
                    'severity': 'warning',
                    'message': restrictions['warnings'].get('high_carbs', 'Yüksek karbonhidrat'),
                    'details': f"Karbonhidrat: {carbs}g/100g (Önerilen: max {restrictions['max_carbs']}g)",
                    'turkish_title': 'Karbonhidrat Uyarısı'
                })
        
        # Sodyum kontrolü
        if 'max_sodium' in restrictions:
            sodium = nutriments.get('sodium_100g', 0) * 1000  # mg'ye çevir
            if sodium > restrictions['max_sodium']:
                alerts.append({
                    'type': 'medical_warning',
                    'condition': condition,
                    'severity': 'critical',
                    'message': restrictions['warnings'].get('high_sodium', 'Yüksek sodyum içeriği'),
                    'details': f"Sodyum: {sodium:.0f}mg/100g (Önerilen: max {restrictions['max_sodium']}mg)",
                    'turkish_title': 'Yüksek Sodyum Uyarısı'
                })
        
        # Tuz kontrolü
        if 'max_salt' in restrictions:
            salt = nutriments.get('salt_100g', 0)
            if salt > restrictions['max_salt']:
                alerts.append({
                    'type': 'medical_warning',
                    'condition': condition,
                    'severity': 'critical',
                    'message': restrictions['warnings'].get('high_sodium', 'Yüksek tuz içeriği'),
                    'details': f"Tuz: {salt}g/100g (Önerilen: max {restrictions['max_salt']}g)",
                    'turkish_title': 'Yüksek Tuz Uyarısı'
                })
        
        # Doymuş yağ kontrolü
        if 'max_saturated_fat' in restrictions:
            sat_fat = nutriments.get('saturated-fat_100g', 0)
            if sat_fat > restrictions['max_saturated_fat']:
                alerts.append({
                    'type': 'medical_warning',
                    'condition': condition,
                    'severity': 'warning',
                    'message': restrictions['warnings'].get('high_saturated_fat', 'Yüksek doymuş yağ'),
                    'details': f"Doymuş yağ: {sat_fat}g/100g (Önerilen: max {restrictions['max_saturated_fat']}g)",
                    'turkish_title': 'Doymuş Yağ Uyarısı'
                })
        
        # Yasaklı malzemeler kontrolü
        if 'avoid_ingredients' in restrictions:
            for ingredient in restrictions['avoid_ingredients']:
                if ingredient.lower() in ingredients_text:
                    alerts.append({
                        'type': 'medical_warning',
                        'condition': condition,
                        'severity': 'critical',
                        'message': f"{ingredient} içeriği {condition} için uygun değil",
                        'details': f"Ürün {ingredient} içermektedir",
                        'turkish_title': 'Yasaklı Malzeme Uyarısı'
                    })
        
        return alerts
    
    def _check_critical_restrictions(self, condition: str, restrictions: Dict, 
                                   nutriments: Dict, ingredients_text: str) -> List[Dict[str, Any]]:
        """Sadece kritik kısıtlamaları kontrol et"""
        alerts = []
        
        # Kritik sodyum kontrolü
        if 'max_sodium' in restrictions:
            sodium = nutriments.get('sodium_100g', 0) * 1000
            if sodium > restrictions['max_sodium']:
                alerts.append({
                    'type': 'critical_medical_warning',
                    'condition': condition,
                    'severity': 'critical',
                    'message': f"Kritik sodyum seviyesi: {sodium:.0f}mg/100g",
                    'turkish_title': 'KRİTİK: Yüksek Sodyum'
                })
        
        # Yasaklı malzemeler (kritik)
        if 'avoid_ingredients' in restrictions:
            for ingredient in restrictions['avoid_ingredients']:
                if ingredient.lower() in ingredients_text:
                    alerts.append({
                        'type': 'critical_medical_warning',
                        'condition': condition,
                        'severity': 'critical',
                        'message': f"Yasaklı malzeme: {ingredient}",
                        'turkish_title': 'KRİTİK: Yasaklı Malzeme'
                    })
        
        return alerts
    
    def _generate_medical_recommendations(self, condition: str, restrictions: Dict, 
                                        nutriments: Dict) -> List[Dict[str, Any]]:
        """Tıbbi duruma özel öneriler oluştur"""
        recommendations = []
        
        # Durum bazlı genel öneriler
        condition_recommendations = {
            'diabetes_type_1': [
                "Karbonhidrat sayımı yaparak insulin dozajını ayarlayın",
                "Düşük glisemik indeksli yiyecekleri tercih edin",
                "Kan şekerinizi düzenli ölçün"
            ],
            'diabetes_type_2': [
                "Porsiyon kontrolü yapın",
                "Lif açısından zengin yiyecekleri tercih edin",
                "Düzenli egzersiz yapın"
            ],
            'hypertension': [
                "DASH diyeti prensiplerini uygulayın",
                "Potasyum açısından zengin yiyecekleri tercih edin",
                "Tuz yerine baharat kullanın"
            ],
            'high_cholesterol': [
                "Omega-3 açısından zengin balıkları tercih edin",
                "Çözünür lif açısından zengin yiyecekleri tüketin",
                "Trans yağlardan tamamen kaçının"
            ]
        }
        
        if condition in condition_recommendations:
            for rec in condition_recommendations[condition]:
                recommendations.append({
                    'type': 'medical_recommendation',
                    'condition': condition,
                    'message': rec,
                    'priority': 'medium'
                })
        
        return recommendations
    
    def _calculate_medical_score(self, alerts: List[Dict[str, Any]]) -> int:
        """Tıbbi uygunluk skoru hesapla (0-100)"""
        if not alerts:
            return 100
        
        base_score = 100
        
        for alert in alerts:
            if alert.get('severity') == 'critical':
                base_score -= 25
            elif alert.get('severity') == 'warning':
                base_score -= 10
            else:
                base_score -= 5
        
        return max(0, base_score)