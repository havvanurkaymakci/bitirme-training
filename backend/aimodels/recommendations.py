# backend/aimodels/recommendations.py
from typing import List, Dict, Any, Optional, Tuple
import logging
import requests
from dataclasses import dataclass
from .alternative_engine import AlternativeEngine
from .medical_warnings import MedicalAnalyzer
from .dietary_warnings import DietaryAnalyzer
from .allergy_warnings import AllergyAnalyzer

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

class RecommendationEngine:
    """Ürün önerisi ve alternatif ürün bulma motoru"""
    
    def __init__(self):
        self.openfoodfacts_base_url = "https://world.openfoodfacts.org"
        # Analiz motorlarını başlat
        self.alternative_engine = AlternativeEngine()
        self.medical_analyzer = MedicalAnalyzer()
        self.dietary_analyzer = DietaryAnalyzer()
        self.allergy_analyzer = AllergyAnalyzer()
    
    def generate_recommendations(self, product_data: Dict[str, Any], user_profile: Dict[str, Any],
                               allergen_results: Dict, medical_results: Dict, 
                               dietary_results: Dict, nutritional_analysis: Dict) -> List[Dict[str, Any]]:
        """
        Kullanıcı profiline göre öneriler ve alternatif ürünler oluştur
        
        Args:
            product_data: Ürün verileri
            user_profile: Kullanıcı profili
            allergen_results: Alerjen analiz sonuçları (geçilmiş analiz)
            medical_results: Tıbbi analiz sonuçları (geçilmiş analiz)
            dietary_results: Diyet analiz sonuçları (geçilmiş analiz)
            nutritional_analysis: Beslenme analizi sonuçları
        """
        recommendations = []
        
        try:
            # 1. Genel beslenme önerileri (mevcut nutritional_analysis'i kullan)
            health_recommendations = self._generate_health_recommendations(
                nutritional_analysis, user_profile
            )
            recommendations.extend(health_recommendations)
            
            # 2. Analiz sonuçlarından öneriler oluştur (kod tekrarı olmadan)
            recommendations.extend(self._generate_recommendations_from_alerts(
                allergen_results, 'allergy'
            ))
            
            recommendations.extend(self._generate_recommendations_from_alerts(
                medical_results, 'medical'
            ))
            
            recommendations.extend(self._generate_recommendations_from_alerts(
                dietary_results, 'dietary'
            ))
            
            # 3. Alternatif ürün önerileri
            alternative_products = self.alternative_engine.find_alternatives(
                product_data, user_profile, nutritional_analysis, max_alternatives=5
            )
            
            if alternative_products:
                formatted_alternatives = self._format_alternatives_for_recommendations(alternative_products)
                
                recommendations.append({
                    'type': 'alternatives',
                    'title': 'Önerilen Alternatif Ürünler',
                    'message': f"{len(alternative_products)} daha sağlıklı alternatif bulundu",
                    'severity': 'info',
                    'category': 'alternatives',
                    'alternatives': formatted_alternatives,
                    'action': 'consider_alternatives',
                    'detailed_alternatives': alternative_products
                })
            
            # 4. Kişiselleştirilmiş ipuçları
            tips = self.get_personalized_tips(user_profile)
            for tip in tips:
                recommendations.append({
                    'type': 'tip',
                    'title': tip['title'],
                    'message': tip['message'],
                    'severity': 'info',
                    'category': tip['category'],
                    'action': 'information'
                })
            
            # Önerileri önem sırasına göre sırala
            recommendations = self._sort_recommendations(recommendations)
            
            return recommendations[:10]  # En fazla 10 öneri döndür
            
        except Exception as e:
            logger.error(f"Öneri oluşturma hatası: {str(e)}")
            return [{
                'type': 'error',
                'title': 'Öneri Hatası',
                'message': 'Öneriler oluşturulamadı',
                'severity': 'info'
            }]
    
    def get_alternatives_only(self, product_data: Dict[str, Any], user_profile: Dict[str, Any], 
                            nutritional_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Sadece alternatif ürün önerilerini döndür
        """
        try:
            alternative_products = self.alternative_engine.find_alternatives(
                product_data, user_profile, nutritional_analysis, max_alternatives=10
            )
            
            if not alternative_products:
                return []
            
            # Frontend için uygun formatta düzenle
            formatted_alternatives = []
            for alt in alternative_products:
                formatted_alt = {
                    'product': {
                        'id': alt.get('barcode', ''),
                        'product_name': alt.get('name', ''),
                        'brands': alt.get('brands', ''),
                        'image_url': alt.get('image_url', ''),
                        'nutrition_grade_fr': alt.get('nutriscore', '').lower(),
                        'nutriments': alt.get('nutrients', {}),
                        'barcode': alt.get('barcode', ''),
                        'labels_tags': alt.get('labels', []),
                        'categories_tags': alt.get('categories', [])
                    },
                    'reasons': alt.get('improvements', []) or [alt.get('reason', 'Daha sağlıklı seçenek')],
                    'score': alt.get('health_score', alt.get('total_score', 0)),
                    'category': alt.get('source_type', 'alternative'),
                    'improvement_details': {
                        'health_score': alt.get('health_score', 0),
                        'total_score': alt.get('total_score', 0),
                        'nutriscore': alt.get('nutriscore', ''),
                        'improvements': alt.get('improvements', [])
                    }
                }
                formatted_alternatives.append(formatted_alt)
            
            return formatted_alternatives
            
        except Exception as e:
            logger.error(f"Alternatif ürün bulma hatası: {str(e)}")
            return []
    
    def _generate_recommendations_from_alerts(self, analysis_results: Dict, analysis_type: str) -> List[Dict[str, Any]]:
        """
        Analiz sonuçlarındaki alertlerden öneriler oluştur
        """
        recommendations = []
        alerts = analysis_results.get('alerts', [])
        
        for alert in alerts:
            recommendation = {
                'type': analysis_type,
                'title': self._get_alert_title(alert, analysis_type),
                'message': alert.get('message', ''),
                'severity': alert.get('severity', 'info'),
                'category': self._get_alert_category(alert, analysis_type),
                'action': self._get_alert_action(alert, analysis_type)
            }
            
            # Ek bilgileri ekle
            if analysis_type == 'allergy':
                recommendation['allergen'] = alert.get('allergen')
                recommendation['allergen_name'] = alert.get('allergen_name')
                recommendation['confidence'] = alert.get('confidence')
            elif analysis_type == 'medical':
                recommendation['condition'] = alert.get('condition')
                recommendation['details'] = alert.get('details')
            elif analysis_type == 'dietary':
                recommendation['preference'] = alert.get('preference')
                recommendation['preference_name'] = alert.get('preference_name')
            
            recommendations.append(recommendation)
        
        return recommendations
    
    def _get_alert_title(self, alert: Dict, analysis_type: str) -> str:
        """Alert için uygun başlık oluştur"""
        if analysis_type == 'allergy':
            return f"Alerjen Uyarısı: {alert.get('allergen_name', 'Bilinmeyen')}"
        elif analysis_type == 'medical':
            return f"Tıbbi Uyarı: {alert.get('details', alert.get('message', ''))}"
        elif analysis_type == 'dietary':
            return f"Diyet Uyumsuzluğu: {alert.get('preference_name', 'Bilinmeyen')}"
        else:
            return alert.get('message', 'Uyarı')
    
    def _get_alert_category(self, alert: Dict, analysis_type: str) -> str:
        """Alert için kategori belirle"""
        if analysis_type == 'allergy':
            return 'allergen'
        elif analysis_type == 'medical':
            return alert.get('condition', 'medical_condition')
        elif analysis_type == 'dietary':
            return alert.get('preference', 'diet_preference')
        else:
            return 'general'
    
    def _get_alert_action(self, alert: Dict, analysis_type: str) -> str:
        """Alert için önerilen aksiyon"""
        severity = alert.get('severity', 'info')
        
        if analysis_type == 'allergy' and severity == 'critical':
            return 'avoid_completely'
        elif analysis_type == 'medical' and severity == 'critical':
            return 'consult_doctor'
        elif analysis_type == 'dietary':
            return 'check_alternatives'
        elif severity in ['critical', 'warning']:
            return 'limit_consumption'
        else:
            return 'monitor'
    
    def _format_alternatives_for_recommendations(self, alternatives: List[Dict]) -> List[Dict]:
        """AlternativeEngine sonuçlarını RecommendationEngine formatına dönüştür"""
        formatted = []
        
        for alt in alternatives:
            formatted.append({
                'name': alt.get('name', ''),
                'barcode': alt.get('barcode', ''),
                'nutriscore': alt.get('nutriscore', ''),
                'health_score': alt.get('health_score', 0),
                'improvements': alt.get('improvements', []),
                'reason': alt.get('reason', ''),
                'brands': alt.get('brands', ''),
                'image_url': alt.get('image_url', ''),
                'nutrients': alt.get('nutrients', {}),
                'source_type': alt.get('source_type', ''),
                'total_score': alt.get('total_score', 0),
                'labels': alt.get('labels', [])
            })
        
        return formatted
    
    def _generate_health_recommendations(self, nutritional_analysis: Dict, 
                                       user_profile: Dict) -> List[Dict[str, Any]]:
        """Genel sağlık önerileri (mevcut nutritional_analysis'den)"""
        recommendations = []
        evaluations = nutritional_analysis.get('evaluations', {})
        values = nutritional_analysis.get('values', {})
        
        # Yüksek şeker uyarısı
        if evaluations.get('sugar') == 'high':
            recommendations.append({
                'type': 'nutrition',
                'title': 'Yüksek Şeker İçeriği',
                'message': f'Bu ürün 100g başına {values.get("sugars", 0):.1f}g şeker içeriyor. Günlük şeker alımınızı kontrol etmeyi düşünün.',
                'severity': 'warning',
                'category': 'sugar',
                'action': 'limit_consumption'
            })
        
        # Yüksek tuz uyarısı
        if evaluations.get('salt') == 'high':
            recommendations.append({
                'type': 'nutrition',
                'title': 'Yüksek Tuz İçeriği',
                'message': f'Bu ürün 100g başına {values.get("salt", 0):.1f}g tuz içeriyor. Kalp sağlığınız için tuz alımınızı azaltmayı düşünün.',
                'severity': 'warning',
                'category': 'salt',
                'action': 'limit_consumption'
            })
        
        # Yüksek kalori uyarısı
        if evaluations.get('calories') == 'high':
            recommendations.append({
                'type': 'nutrition',
                'title': 'Yüksek Kalori İçeriği',
                'message': f'Bu ürün 100g başına {values.get("energy_kcal", 0):.0f} kalori içeriyor. Porsiyon kontrolü yapmanızı öneririz.',
                'severity': 'info',
                'category': 'calories',
                'action': 'portion_control'
            })
        
        # Düşük lif uyarısı
        if values.get('fiber', 0) < 3:
            recommendations.append({
                'type': 'nutrition',
                'title': 'Düşük Lif İçeriği',
                'message': 'Bu ürün düşük lif içeriyor. Sindirim sağlığınız için lifli gıdalar tüketmeyi artırın.',
                'severity': 'info',
                'category': 'fiber',
                'action': 'increase_fiber'
            })
        
        return recommendations
    
    def _sort_recommendations(self, recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Önerileri önem sırasına göre sırala"""
        severity_order = {'critical': 0, 'warning': 1, 'info': 2}
        return sorted(recommendations, 
                     key=lambda x: (severity_order.get(x.get('severity', 'info'), 2),
                                   x.get('type', '')))
    
    def get_personalized_tips(self, user_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Kullanıcı profiline göre kişiselleştirilmiş ipuçları"""
        tips = []
        
        health_conditions = user_profile.get('health_conditions', [])
        dietary_preferences = user_profile.get('dietary_preferences', [])
        allergies = user_profile.get('allergies', [])
        
        # Diyabet ipuçları
        if any(cond in ['diabetes_type_1', 'diabetes_type_2', 'prediabetes'] 
               for cond in health_conditions):
            tips.append({
                'title': 'Diyabet Yönetimi',
                'message': 'Ürün seçerken şeker içeriğini kontrol edin ve karbonhidrat sayımı yapın.',
                'category': 'diabetes'
            })
        
        # Hipertansiyon ipuçları
        if 'hypertension' in health_conditions:
            tips.append({
                'title': 'Tansiyonu Kontrol Altında Tutun',
                'message': 'Düşük sodyumlu ürünleri tercih edin ve DASH diyeti prensiplerini uygulayın.',
                'category': 'hypertension'
            })
        
        # Vegan ipuçları
        if 'vegan' in dietary_preferences:
            tips.append({
                'title': 'Vegan Beslenme',
                'message': 'B12 vitamini ve protein kaynakları için etiketleri dikkatli okuyun.',
                'category': 'vegan'
            })
        
        # Glütensiz ipuçları
        if 'gluten_free' in dietary_preferences:
            tips.append({
                'title': 'Glütensiz Yaşam',
                'message': 'Çapraz bulaşma riskine dikkat edin ve sertifikalı ürünleri tercih edin.',
                'category': 'gluten_free'
            })
        
        # Alerji ipuçları
        if allergies:
            tips.append({
                'title': 'Alerji Güvenliği',
                'message': 'Her zaman etiketleri dikkatli okuyun ve şüpheli durumlarda üreticiyle iletişime geçin.',
                'category': 'allergy_safety'
            })
        
        return tips
    
    def get_quick_safety_check(self, product_data: Dict[str, Any], user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hızlı güvenlik kontrolü - sadece kritik uyarılar
        """
        try:
            critical_issues = []
            
            # Kritik alerjen kontrolü
            if user_profile.get('allergies'):
                critical_allergens = self.allergy_analyzer.get_critical_allergens(
                    product_data, user_profile['allergies']
                )
                critical_issues.extend(critical_allergens)
            
            # Kritik tıbbi uyarılar
            if user_profile.get('health_conditions'):
                critical_medical = self.medical_analyzer.get_critical_warnings(
                    product_data, user_profile['health_conditions']
                )
                critical_issues.extend(critical_medical.get('alerts', []))
            
            # Kritik diyet uyarıları
            if user_profile.get('dietary_preferences'):
                critical_dietary = self.dietary_analyzer.get_critical_warnings(
                    product_data, user_profile['dietary_preferences']
                )
                critical_issues.extend(critical_dietary.get('alerts', []))
            
            is_safe = len(critical_issues) == 0
            
            return {
                'is_safe': is_safe,
                'critical_issues': critical_issues,
                'total_critical': len(critical_issues)
            }
            
        except Exception as e:
            logger.error(f"Hızlı güvenlik kontrolü hatası: {str(e)}")
            return {
                'is_safe': False,
                'critical_issues': [],
                'total_critical': 0,
                'error': str(e)
            }