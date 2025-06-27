# backend/aimodels/product_analysis.py
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from .rule_engine.allergy_warnings import AllergyAnalyzer
from .rule_engine.medical_warnings import MedicalAnalyzer
from .rule_engine.dietary_warnings import DietaryAnalyzer
from .rule_engine.personalization.recommendations import RecommendationEngine

logger = logging.getLogger(__name__)

@dataclass
class AnalysisResult:
    """Analiz sonucu veri yapısı"""
    health_score: int  # 0-100 arası sağlık skoru
    is_suitable: bool  # Kullanıcı için uygun mu?
    warnings: List[Dict[str, Any]]  # Uyarılar
    recommendations: List[Dict[str, Any]]  # Öneriler
    nutritional_analysis: Dict[str, Any]  # Beslenme analizi
    allergen_alerts: List[Dict[str, Any]]  # Alerjen uyarıları
    medical_alerts: List[Dict[str, Any]]  # Tıbbi uyarılar
    dietary_compliance: Dict[str, Any]  # Diyet uyumluluğu
    summary: str  # Genel özet
    confidence_score: int  # Analiz güven skoru
    analysis_timestamp: str  # Analiz zamanı

class ProductAnalyzer:
    """Ana ürün analiz sınıfı"""
    
    def __init__(self):
        self.allergy_analyzer = AllergyAnalyzer()
        self.medical_analyzer = MedicalAnalyzer()
        self.dietary_analyzer = DietaryAnalyzer()
        self.recommendation_engine = RecommendationEngine()
    
    def analyze_detailed(self, product_data: Dict[str, Any], user_profile: Dict[str, Any]) -> AnalysisResult:
        """Ana analiz metodu - tam analiz yapar"""
        try:
            # Veri doğrulama
            if not self._validate_product_data(product_data):
                return self._create_error_response("Geçersiz ürün verisi")
            
            # Kullanıcı profili normalize et
            normalized_profile = self._normalize_user_profile(user_profile)
            
            # Alt analizleri çalıştır
            allergen_results = self.allergy_analyzer.analyze_detailed(
                product_data, normalized_profile.get('allergies', [])
            )
            medical_results = self.medical_analyzer.analyze_detailed(
                product_data, normalized_profile.get('health_conditions', [])
            )
            dietary_results = self.dietary_analyzer.analyze_detailed(
                product_data, normalized_profile.get('dietary_preferences', [])
            )
            nutritional_analysis = self._analyze_nutrition(product_data, normalized_profile)
            
            # Sağlık skoru hesapla
            health_score = self._calculate_health_score(
                product_data, allergen_results, medical_results, 
                dietary_results, nutritional_analysis
            )
            
            # Uygunluk değerlendirmesi
            is_suitable = self._evaluate_suitability(
                allergen_results, medical_results, dietary_results, health_score
            )
            
            # Uyarıları birleştir
            all_warnings = self._combine_warnings(
                allergen_results, medical_results, dietary_results
            )
            
            # Öneriler oluştur - DÜZELTME: Doğru parametreler gönder
            recommendations = self.recommendation_engine.generate_recommendations(
                product_data, normalized_profile, allergen_results, 
                medical_results, dietary_results, nutritional_analysis
            )
            
            # Özet oluştur
            product_name = product_data.get('product_name', 'Bilinmeyen Ürün')
            summary = self._generate_summary(
                health_score, is_suitable, len(all_warnings), 
                len(recommendations), product_name
            )
            
            # Güven skoru hesapla
            confidence_score = self._calculate_confidence_score(product_data, normalized_profile)
            
            # Sonucu oluştur
            result = AnalysisResult(
                health_score=health_score,
                is_suitable=is_suitable,
                warnings=all_warnings,
                recommendations=recommendations,
                nutritional_analysis=nutritional_analysis,
                allergen_alerts=allergen_results.get('alerts', []),
                medical_alerts=medical_results.get('alerts', []),
                dietary_compliance=dietary_results,
                summary=summary,
                confidence_score=confidence_score,
                analysis_timestamp=self._get_timestamp()
            )
            
            logger.info(f"Ürün analizi tamamlandı: {product_name}, Skor: {health_score}")
            return result
            
        except Exception as e:
            logger.error(f"Analiz hatası: {str(e)}")
            return self._create_error_response(f"Analiz hatası: {str(e)}")
    
    # EKLEME: Views.py'nin beklediği metod
    def analyze_product_complete(self, product_data: Dict[str, Any], user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Kapsamlı ürün analizi - views.py için uyumlu"""
        result = self.analyze_detailed(product_data, user_profile)
        
        # AnalysisResult'ı dictionary'ye çevir
        return {
            'health_score': result.health_score,
            'is_suitable': result.is_suitable,
            'warnings': result.warnings,
            'recommendations': result.recommendations,
            'nutritional_analysis': result.nutritional_analysis,
            'allergen_alerts': result.allergen_alerts,
            'medical_alerts': result.medical_alerts,
            'dietary_compliance': result.dietary_compliance,
            'summary': result.summary,
            'confidence_score': result.confidence_score,
            'analysis_timestamp': result.analysis_timestamp,
            'health_alerts': result.warnings  # views.py'nin beklediği alan
        }
    
    def analyze_warnings_only(self, product_data: Dict[str, Any], user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Sadece uyarıları analiz et (daha hızlı)"""
        try:
            normalized_profile = self._normalize_user_profile(user_profile)
            
            allergen_results = self.allergy_analyzer.analyze_detailed(
                product_data, normalized_profile.get('allergies', [])
            )
            
            # Medical ve dietary analizörlerin get_critical_warnings metodları varsa kullan
            medical_results = getattr(self.medical_analyzer, 'get_critical_warnings', 
                                    self.medical_analyzer.analyze_detailed)(
                product_data, normalized_profile.get('health_conditions', [])
            )
            dietary_results = getattr(self.dietary_analyzer, 'get_critical_warnings', 
                                    self.dietary_analyzer.analyze_detailed)(
                product_data, normalized_profile.get('dietary_preferences', [])
            )
            
            all_warnings = self._combine_warnings(allergen_results, medical_results, dietary_results)
            
            return {
                'warnings': all_warnings,
                'allergen_alerts': allergen_results.get('alerts', []),
                'medical_alerts': medical_results.get('alerts', []),
                'dietary_alerts': dietary_results.get('alerts', []),
                'critical_issues': len([w for w in all_warnings if w.get('severity') == 'critical']),
                'product_name': product_data.get('product_name', 'Bilinmeyen Ürün'),
                'analysis_timestamp': self._get_timestamp(),
                'health_alerts': all_warnings  # views.py'nin beklediği alan
            }
            
        except Exception as e:
            logger.error(f"Uyarı analizi hatası: {str(e)}")
            return {'error': f"Uyarı analizi hatası: {str(e)}"}
    
    def apply_filters(self, products: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Ürünleri filtreleme fonksiyonu - views.py'den taşındı
        """
        if not filters:
            return products
            
        filtered_products = []
        
        for product in products:
            # Skip products without required data
            if not product:
                continue
                
            # Nutriments kontrolü
            nutriments = product.get('nutriments', {})
            if not nutriments:
                continue
                
            include_product = True
            
            # Energy (kcal) filter
            if 'max_energy_kcal' in filters and include_product:
                energy = nutriments.get('energy-kcal_100g') or nutriments.get('energy-kcal')
                if energy and energy > filters['max_energy_kcal']:
                    include_product = False
                    
            # Sugar filter
            if 'max_sugar' in filters and include_product:
                sugar = nutriments.get('sugars_100g') or nutriments.get('sugars')
                if sugar and sugar > filters['max_sugar']:
                    include_product = False
                    
            # Fat filter
            if 'max_fat' in filters and include_product:
                fat = nutriments.get('fat_100g') or nutriments.get('fat')
                if fat and fat > filters['max_fat']:
                    include_product = False
                    
            # Saturated fat filter
            if 'max_saturated_fat' in filters and include_product:
                sat_fat = nutriments.get('saturated-fat_100g') or nutriments.get('saturated-fat')
                if sat_fat and sat_fat > filters['max_saturated_fat']:
                    include_product = False
                    
            # Salt filter
            if 'max_salt' in filters and include_product:
                salt = nutriments.get('salt_100g') or nutriments.get('salt')
                if salt and salt > filters['max_salt']:
                    include_product = False
                    
            # Sodium filter
            if 'max_sodium' in filters and include_product:
                sodium = nutriments.get('sodium_100g') or nutriments.get('sodium')
                if sodium and sodium > filters['max_sodium']:
                    include_product = False
                    
            # Fiber filter (minimum)
            if 'min_fiber' in filters and include_product:
                fiber = nutriments.get('fiber_100g') or nutriments.get('fiber')
                if not fiber or fiber < filters['min_fiber']:
                    include_product = False
                    
            # Protein filters
            if 'min_proteins' in filters and include_product:
                proteins = nutriments.get('proteins_100g') or nutriments.get('proteins')
                if not proteins or proteins < filters['min_proteins']:
                    include_product = False
                    
            if 'max_proteins' in filters and include_product:
                proteins = nutriments.get('proteins_100g') or nutriments.get('proteins')
                if proteins and proteins > filters['max_proteins']:
                    include_product = False
                    
            # Vegan/Vegetarian filters
            if 'is_vegan' in filters and filters['is_vegan'] and include_product:
                labels = product.get('labels_tags', [])
                if 'en:vegan' not in labels:
                    include_product = False
                    
            if 'is_vegetarian' in filters and filters['is_vegetarian'] and include_product:
                labels = product.get('labels_tags', [])
                if 'en:vegetarian' not in labels and 'en:vegan' not in labels:
                    include_product = False
                    
            # Nutriscore filter
            if 'nutriscore_grade' in filters and include_product:
                nutriscore = product.get('nutriscore_grade', '').upper()
                if nutriscore not in filters['nutriscore_grade']:
                    include_product = False
                    
            # NOVA group filter
            if 'nova_group' in filters and include_product:
                nova = str(product.get('nova_group', ''))
                if nova not in [str(group) for group in filters['nova_group']]:
                    include_product = False
                    
            # Ingredients filters
            if 'include_ingredients' in filters and include_product:
                ingredients_text = product.get('ingredients_text', '').lower()
                for ingredient in filters['include_ingredients']:
                    if ingredient.lower() not in ingredients_text:
                        include_product = False
                        break
                        
            if 'exclude_ingredients' in filters and include_product:
                ingredients_text = product.get('ingredients_text', '').lower()
                for ingredient in filters['exclude_ingredients']:
                    if ingredient.lower() in ingredients_text:
                        include_product = False
                        break
            
            if include_product:
                filtered_products.append(product)
        
        return filtered_products
    
    def parse_filter_params(self, request_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Request parametrelerini filter formatına çevirir
        """
        filter_keys = [
            'max_energy_kcal', 'max_sugar', 'max_fat', 'max_saturated_fat',
            'max_salt', 'max_sodium', 'min_fiber', 'min_proteins', 'max_proteins',
            'is_vegan', 'is_vegetarian', 'nutriscore_grade', 'nova_group',
        ]
        filters = {}

        for key in filter_keys:
            value = request_params.get(key)
            if value is not None:
                if key in ['is_vegan', 'is_vegetarian']:
                    filters[key] = str(value).lower() == 'true'
                elif key in ['nutriscore_grade', 'nova_group']:
                    if value:
                        filters[key] = value.upper().split(',') if ',' in str(value) else [str(value).upper()]
                else:
                    try:
                        filters[key] = float(value)
                    except (ValueError, TypeError):
                        continue

        # include_ingredients ve exclude_ingredients virgülle ayrılabilir
        include = request_params.get('include_ingredients', '')
        exclude = request_params.get('exclude_ingredients', '')
        if include:
            filters['include_ingredients'] = [item.strip() for item in str(include).split(',')]
        if exclude:
            filters['exclude_ingredients'] = [item.strip() for item in str(exclude).split(',')]

        return filters
    
    def _normalize_user_profile(self, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Kullanıcı profil verilerini normalize et"""
        if not user_profile:
            return {}
        
        normalized = {
            'user_id': user_profile.get('id') or user_profile.get('user_id'),
            'allergies': user_profile.get('allergies', []) or [],
            'health_conditions': user_profile.get('health_conditions', []) or [],
            'dietary_preferences': user_profile.get('dietary_preferences', []) or [],
            'age': user_profile.get('age'),
            'gender': user_profile.get('gender'),
            'activity_level': user_profile.get('activity_level'),
            'health_goals': user_profile.get('health_goals', []) or []
        }
        
        # Liste türündeki alanları kontrol et
        for key in ['allergies', 'health_conditions', 'dietary_preferences', 'health_goals']:
            if normalized[key] and not isinstance(normalized[key], list):
                normalized[key] = []
        
        return normalized
    
    def _validate_product_data(self, product_data: Dict[str, Any]) -> bool:
        """Ürün verisinin geçerliliğini kontrol et"""
        if not product_data:
            return False
        
        # En az bir tanımlayıcı alan olmalı
        identifiers = ['id', '_id', 'product_name', 'product_name_tr']
        has_identifier = any(product_data.get(field) for field in identifiers)
        
        return has_identifier
    
    def _analyze_nutrition(self, product_data: Dict[str, Any], user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Beslenme değerlerini analiz et"""
        nutriments = product_data.get('nutriments', {})
        
        # 100g başına değerleri al
        values = {
            'energy_kcal': self._safe_get_float(nutriments, 'energy-kcal_100g') or 
                          self._safe_get_float(nutriments, 'energy-kcal'),
            'fat': self._safe_get_float(nutriments, 'fat_100g') or 
                  self._safe_get_float(nutriments, 'fat'),
            'saturated_fat': self._safe_get_float(nutriments, 'saturated-fat_100g') or 
                           self._safe_get_float(nutriments, 'saturated-fat'),
            'sugars': self._safe_get_float(nutriments, 'sugars_100g') or 
                     self._safe_get_float(nutriments, 'sugars'),
            'salt': self._safe_get_float(nutriments, 'salt_100g') or 
                   self._safe_get_float(nutriments, 'salt'),
            'sodium': self._safe_get_float(nutriments, 'sodium_100g') or 
                     self._safe_get_float(nutriments, 'sodium'),
            'proteins': self._safe_get_float(nutriments, 'proteins_100g') or 
                       self._safe_get_float(nutriments, 'proteins'),
            'fiber': self._safe_get_float(nutriments, 'fiber_100g') or 
                    self._safe_get_float(nutriments, 'fiber'),
            'carbohydrates': self._safe_get_float(nutriments, 'carbohydrates_100g') or 
                           self._safe_get_float(nutriments, 'carbohydrates')
        }
        
        # Değerlendirmeler
        evaluations = self._evaluate_nutrition_levels(values)
        
        # Sağlık göstergeleri
        health_markers = self._calculate_health_markers(values)
        
        analysis = {
            'values': values,  # DÜZELTME: nutrition_per_100g yerine values
            'evaluations': evaluations,
            'health_markers': health_markers,
            'nutriscore': product_data.get('nutriscore_grade', '').upper(),
            'nova_group': product_data.get('nova_group', 0),
            'has_complete_nutrition': self._has_complete_nutrition(values),
            'quality_rating': self._assess_nutrition_quality(values)
        }
        
        return analysis
    
    def _safe_get_float(self, data: Dict, key: str) -> float:
        """Güvenli float değeri alma"""
        try:
            value = data.get(key)
            return float(value) if value is not None else 0.0
        except (ValueError, TypeError):
            return 0.0
    
    def _evaluate_nutrition_levels(self, nutrition: Dict[str, float]) -> Dict[str, str]:
        """Beslenme değerlerini seviyelerine göre değerlendir"""
        evaluations = {}
        
        # Kalori değerlendirmesi
        calories = nutrition.get('energy_kcal', 0)
        if calories > 500:
            evaluations['calories'] = 'high'
        elif calories > 200:
            evaluations['calories'] = 'moderate'
        else:
            evaluations['calories'] = 'low'
        
        # Şeker değerlendirmesi
        sugars = nutrition.get('sugars', 0)
        if sugars > 15:
            evaluations['sugar'] = 'high'
        elif sugars > 5:
            evaluations['sugar'] = 'moderate'
        else:
            evaluations['sugar'] = 'low'
        
        # Yağ değerlendirmesi
        fat = nutrition.get('fat', 0)
        if fat > 20:
            evaluations['fat'] = 'high'
        elif fat > 10:
            evaluations['fat'] = 'moderate'
        else:
            evaluations['fat'] = 'low'
        
        # Tuz değerlendirmesi
        salt = nutrition.get('salt', 0)
        if salt > 1.5:
            evaluations['salt'] = 'high'
        elif salt > 0.5:
            evaluations['salt'] = 'moderate'
        else:
            evaluations['salt'] = 'low'
        
        return evaluations
    
    def _has_complete_nutrition(self, nutrition: Dict[str, float]) -> bool:
        """Beslenme verilerinin eksiksiz olup olmadığını kontrol et"""
        essential_nutrients = ['energy_kcal', 'fat', 'sugars', 'salt', 'proteins']
        valid_count = sum(1 for nutrient in essential_nutrients 
                         if nutrition.get(nutrient, 0) > 0)
        return valid_count >= 3
    
    def _assess_nutrition_quality(self, nutrition: Dict[str, float]) -> str:
        """Beslenme kalitesini değerlendir"""
        score = 0
        
        # Kalori kontrolü
        calories = nutrition.get('energy_kcal', 0)
        if calories < 300:
            score += 1
        elif calories > 500:
            score -= 1
        
        # Yağ kontrolü
        fat = nutrition.get('fat', 0)
        if fat < 10:
            score += 1
        elif fat > 20:
            score -= 1
        
        # Şeker kontrolü
        sugars = nutrition.get('sugars', 0)
        if sugars < 5:
            score += 1
        elif sugars > 15:
            score -= 2
        
        # Tuz kontrolü
        salt = nutrition.get('salt', 0)
        if salt < 0.5:
            score += 1
        elif salt > 1.5:
            score -= 2
        
        # Protein kontrolü
        proteins = nutrition.get('proteins', 0)
        if proteins > 10:
            score += 1
        
        # Lif kontrolü
        fiber = nutrition.get('fiber', 0)
        if fiber > 5:
            score += 1
        
        if score >= 2:
            return 'excellent'
        elif score >= 0:
            return 'good'
        elif score >= -2:
            return 'fair'
        else:
            return 'poor'
    
    def _calculate_health_markers(self, nutrition: Dict[str, float]) -> Dict[str, bool]:
        """Sağlık göstergelerini hesapla"""
        return {
            'high_sodium': nutrition.get('sodium', 0) > 600,  # 600mg/100g
            'high_sugar': nutrition.get('sugars', 0) > 15,     # 15g/100g
            'high_fat': nutrition.get('fat', 0) > 20,          # 20g/100g
            'high_saturated_fat': nutrition.get('saturated_fat', 0) > 5,  # 5g/100g
            'good_protein': nutrition.get('proteins', 0) > 10,  # 10g/100g
            'good_fiber': nutrition.get('fiber', 0) > 5         # 5g/100g
        }
    
    def _calculate_health_score(self, product_data: Dict[str, Any], allergen_results: Dict, 
                               medical_results: Dict, dietary_results: Dict, 
                               nutritional_analysis: Dict) -> int:
        """0-100 arası sağlık skoru hesapla"""
        base_score = 50  # Başlangıç skoru
        
        # Nutriscore'a göre ayarlama
        nutriscore = product_data.get('nutriscore_grade', '').upper()
        nutriscore_adjustments = {'A': 20, 'B': 10, 'C': 0, 'D': -10, 'E': -20}
        base_score += nutriscore_adjustments.get(nutriscore, 0)
        
        # NOVA grubuna göre ayarlama
        nova_group = product_data.get('nova_group', 0)
        nova_adjustments = {1: 15, 2: 5, 3: -5, 4: -15}
        base_score += nova_adjustments.get(nova_group, 0)
        
        # Beslenme kalitesine göre ayarlama
        quality_rating = nutritional_analysis.get('quality_rating', 'fair')
        quality_adjustments = {'excellent': 15, 'good': 5, 'fair': -5, 'poor': -15}
        base_score += quality_adjustments.get(quality_rating, 0)
        
        # Uyarılara göre ayarlama
        critical_warnings = 0
        for result in [allergen_results, medical_results, dietary_results]:
            alerts = result.get('alerts', [])
            critical_warnings += len([a for a in alerts if a.get('severity') == 'critical'])
        
        base_score -= critical_warnings * 15
        
        # 0-100 arasında sınırla
        return max(0, min(100, base_score))
    
    def _evaluate_suitability(self, allergen_results: Dict, medical_results: Dict, 
                             dietary_results: Dict, health_score: int) -> bool:
        """Genel uygunluk değerlendirmesi"""
        # Kritik uyarı var mı?
        has_critical_alerts = any(
            any(alert.get('severity') == 'critical' for alert in results.get('alerts', []))
            for results in [allergen_results, medical_results, dietary_results]
        )
        
        if has_critical_alerts:
            return False
        
        # Sağlık skoru çok düşük mü?
        if health_score < 30:
            return False
        
        return True
    
    def _combine_warnings(self, allergen_results: Dict, medical_results: Dict, 
                         dietary_results: Dict) -> List[Dict[str, Any]]:
        """Tüm uyarıları birleştir ve önceliklendir"""
        all_warnings = []
        
        # Her modülden uyarıları al
        for results in [allergen_results, medical_results, dietary_results]:
            alerts = results.get('alerts', [])
            all_warnings.extend(alerts)
        
        # Önem sırasına göre sırala (critical -> high -> medium -> low)
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        all_warnings.sort(key=lambda x: severity_order.get(x.get('severity', 'low'), 4))
        
        return all_warnings
    
    def _generate_summary(self, health_score: int, is_suitable: bool, 
                         warning_count: int, recommendation_count: int, 
                         product_name: str) -> str:
        """Genel özet oluştur"""
        if not is_suitable:
            return f"{product_name} sizin için uygun değil. {warning_count} önemli uyarı bulundu."
        
        if health_score >= 80:
            return f"{product_name} sağlıklı bir seçim! Sağlık skoru: {health_score}/100"
        elif health_score >= 60:
            return f"{product_name} kabul edilebilir bir seçim. Sağlık skoru: {health_score}/100"
        elif health_score >= 40:
            return f"{product_name} orta düzeyde sağlıklı. {recommendation_count} öneri var."
        else:
            return f"{product_name} sağlık açısından ideal değil. Daha sağlıklı alternatifler düşünün."
    
    def _calculate_confidence_score(self, product_data: Dict[str, Any], user_profile: Dict[str, Any]) -> int:
        """Analiz güven skoru (0-100)"""
        confidence = 50
        
        # Ürün verisi eksiksizliği
        if product_data.get('nutriments'):
            confidence += 20
        if product_data.get('ingredients_text'):
            confidence += 15
        if product_data.get('allergens_tags'):
            confidence += 10
        
        # Kullanıcı profil eksiksizliği
        if user_profile.get('allergies'):
            confidence += 5
        if user_profile.get('health_conditions'):
            confidence += 5
        if user_profile.get('dietary_preferences'):
            confidence += 5
        
        return min(100, confidence)
    
    def _create_error_response(self, error_message: str) -> AnalysisResult:
        """Hata durumu için standart yanıt"""
        return AnalysisResult(
            health_score=0,
            is_suitable=False,
            warnings=[],
            recommendations=[],
            nutritional_analysis={},
            allergen_alerts=[],
            medical_alerts=[],
            dietary_compliance={},
            summary=f"Analiz hatası: {error_message}",
            confidence_score=0,
            analysis_timestamp=self._get_timestamp()
        )
    
    def _get_timestamp(self) -> str:
        """Zaman damgası"""
        return datetime.now().isoformat()