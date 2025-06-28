# backend/aimodels/product_analysis.py
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from .rule_engine.allergy_warnings import AllergyAnalyzer
from .rule_engine.medical_warnings import MedicalAnalyzer
from .rule_engine.dietary_warnings import DietaryAnalyzer

logger = logging.getLogger(__name__)

@dataclass
class RuleBasedAnalysisResult:
    """Kural tabanlı analiz sonucu veri yapısı"""
    health_score: int  # 0-100 arası temel sağlık skoru (ML'siz)
    is_suitable: bool  # Kullanıcı için uygun mu?
    warnings: List[Dict[str, Any]]  # Uyarılar
    recommendations: List[Dict[str, Any]]  # Temel öneriler
    nutritional_analysis: Dict[str, Any]  # Beslenme analizi
    allergen_alerts: List[Dict[str, Any]]  # Alerjen uyarıları
    medical_alerts: List[Dict[str, Any]]  # Tıbbi uyarılar
    dietary_compliance: Dict[str, Any]  # Diyet uyumluluğu
    summary: str  # Genel özet
    confidence_score: int  # Analiz güven skoru
    analysis_timestamp: str  # Analiz zamanı
    analysis_type: str = "rule_based"  # Analiz türü

class ProductAnalyzer:
    """Kural tabanlı ürün analiz sınıfı - ML bileşenleri kaldırıldı"""
    
    def __init__(self):
        self.allergy_analyzer = AllergyAnalyzer()
        self.medical_analyzer = MedicalAnalyzer()
        self.dietary_analyzer = DietaryAnalyzer()
    
    def analyze_detailed(self, product_data: Dict[str, Any], user_profile: Dict[str, Any]) -> RuleBasedAnalysisResult:
        """Ana analiz metodu - sadece kural tabanlı analiz yapar"""
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
            
            # Kural tabanlı sağlık skoru hesapla
            health_score = self._calculate_rule_based_health_score(
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
            
            # Kural tabanlı öneriler oluştur
            recommendations = self._generate_rule_based_recommendations(
                product_data, normalized_profile, allergen_results, 
                medical_results, dietary_results, nutritional_analysis
            )
            
            # Özet oluştur
            product_name = product_data.get('product_name', 'Bilinmeyen Ürün')
            summary = self._generate_rule_based_summary(
                health_score, is_suitable, len(all_warnings), 
                len(recommendations), product_name
            )
            
            # Güven skoru hesapla
            confidence_score = self._calculate_confidence_score(product_data, normalized_profile)
            
            # Sonucu oluştur
            result = RuleBasedAnalysisResult(
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
            
            logger.info(f"Kural tabanlı analiz tamamlandı: {product_name}, Skor: {health_score}")
            return result
            
        except Exception as e:
            logger.error(f"Analiz hatası: {str(e)}")
            return self._create_error_response(f"Analiz hatası: {str(e)}")
    
    def analyze_product_complete(self, product_data: Dict[str, Any], user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Kapsamlı kural tabanlı ürün analizi - views.py için uyumlu"""
        result = self.analyze_detailed(product_data, user_profile)
        
        # RuleBasedAnalysisResult'ı dictionary'ye çevir
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
            'health_alerts': result.warnings,  # views.py'nin beklediği alan
            'analysis_type': result.analysis_type
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
                'health_alerts': all_warnings,  # views.py'nin beklediği alan
                'analysis_type': 'warnings_only'
            }
            
        except Exception as e:
            logger.error(f"Uyarı analizi hatası: {str(e)}")
            return {'error': f"Uyarı analizi hatası: {str(e)}"}
    
    def analyze_quick(self, product_data: Dict[str, Any], user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Hızlı temel analiz - search için kullanılır"""
        try:
            normalized_profile = self._normalize_user_profile(user_profile)
            
            # Sadece kritik uyarıları kontrol et
            critical_alerts = []
            
            # Alerjen kontrolü
            allergen_results = self.allergy_analyzer.analyze_detailed(
                product_data, normalized_profile.get('allergies', [])
            )
            critical_alerts.extend([
                alert for alert in allergen_results.get('alerts', []) 
                if alert.get('severity') == 'critical'
            ])
            
            # Basit sağlık skoru
            basic_score = 5.0  # Varsayılan skor
            if critical_alerts:
                basic_score = max(1.0, basic_score - len(critical_alerts))
            
            return {
                'basic_health_score': basic_score,
                'critical_alerts': critical_alerts[:2],  # En fazla 2 kritik uyarı
                'has_critical_issues': len(critical_alerts) > 0,
                'analysis_type': 'quick_rule_based'
            }
            
        except Exception as e:
            logger.error(f"Hızlı analiz hatası: {str(e)}")
            return {
                'basic_health_score': 3.0,
                'critical_alerts': [],
                'has_critical_issues': False,
                'error': str(e)
            }

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
            'health_goals': user_profile.get('health_goals', []) or [],
        }
        
        return normalized

    def _calculate_rule_based_health_score(self, product_data: Dict[str, Any], 
                                         allergen_results: Dict[str, Any],
                                         medical_results: Dict[str, Any], 
                                         dietary_results: Dict[str, Any],
                                         nutritional_analysis: Dict[str, Any]) -> int:
        """Sadece kural tabanlı sağlık skoru hesapla"""
        
        # Temel skor (0-100)
        base_score = 70
        
        # Uyarılara göre puan düşür
        allergen_penalties = len(allergen_results.get('alerts', [])) * 15
        medical_penalties = len(medical_results.get('alerts', [])) * 20
        dietary_penalties = len(dietary_results.get('alerts', [])) * 10
        
        # Besin değeri bonusu/cezası
        nutrition_score = nutritional_analysis.get('overall_score', 50)
        nutrition_bonus = (nutrition_score - 50) * 0.3
        
        # Final skor
        final_score = base_score - allergen_penalties - medical_penalties - dietary_penalties + nutrition_bonus
        
        return max(0, min(100, int(final_score)))

    def _generate_rule_based_recommendations(self, product_data: Dict[str, Any],
                                           user_profile: Dict[str, Any],
                                           allergen_results: Dict[str, Any],
                                           medical_results: Dict[str, Any],
                                           dietary_results: Dict[str, Any],
                                           nutritional_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Kural tabanlı temel öneriler"""
        recommendations = []
        
        # Alerjen uyarıları varsa
        if allergen_results.get('alerts'):
            recommendations.append({
                'type': 'allergy_warning',
                'title': 'Alerjen uyarısı',
                'description': 'Bu ürün size alerjik reaksiyon verebilir',
                'priority': 'critical',
                'action': 'avoid_product',
                'source': 'rule_based'
            })
        
        # Tıbbi uyarılar varsa
        if medical_results.get('alerts'):
            recommendations.append({
                'type': 'medical_warning',
                'title': 'Sağlık durumu uyarısı',
                'description': 'Bu ürün sağlık durumunuza uygun olmayabilir',
                'priority': 'high',
                'action': 'consult_doctor',
                'source': 'rule_based'
            })
        
        # Diyet uyumluluğu
        if not dietary_results.get('is_compliant', True):
            recommendations.append({
                'type': 'dietary_warning',
                'title': 'Diyet uyumluluğu',
                'description': 'Bu ürün diyet tercihlerinize uygun değil',
                'priority': 'medium',
                'action': 'find_alternative',
                'source': 'rule_based'
            })
        
        # Beslenme önerileri
        nutrition_score = nutritional_analysis.get('overall_score', 50)
        if nutrition_score < 40:
            recommendations.append({
                'type': 'nutrition_warning',
                'title': 'Beslenme değeri düşük',
                'description': 'Bu ürün beslenme açısından ideal değil',
                'priority': 'medium',
                'action': 'consider_alternatives',
                'source': 'rule_based'
            })
        
        return recommendations

    def _generate_rule_based_summary(self, health_score: int, is_suitable: bool, 
                                   warning_count: int, recommendation_count: int, 
                                   product_name: str) -> str:
        """Kural tabanlı özet oluştur"""
        
        summary = f"{product_name} için kural tabanlı analiz tamamlandı. "
        summary += f"Temel sağlık skoru: {health_score}/100. "
        
        if is_suitable:
            if health_score >= 80:
                summary += "Bu ürün genel olarak iyi bir seçim. "
            elif health_score >= 60:
                summary += "Bu ürün kabul edilebilir bir seçim. "
            else:
                summary += "Bu ürünü dikkatli tüketebilirsiniz. "
        else:
            summary += "Bu ürün sizin için uygun değil. "
        
        if warning_count > 0:
            summary += f"{warning_count} önemli uyarı bulundu. "
        
        if recommendation_count > 0:
            summary += f"{recommendation_count} öneri sunuldu. "
        
        summary += "Kişiselleştirilmiş analiz için ML skorlarını kontrol edin."
        
        return summary.strip()

    def _validate_product_data(self, product_data: Dict[str, Any]) -> bool:
        """Ürün verisi doğrulama"""
        required_fields = ['product_name']
        return all(field in product_data for field in required_fields)

    def _analyze_nutrition(self, product_data: Dict[str, Any], user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Beslenme analizi"""
        # Temel besin analizi implementasyonu
        return {
            'overall_score': 60,  # Varsayılan skor
            'protein_score': 50,
            'fat_score': 50,
            'carb_score': 50,
            'fiber_score': 50,
            'sodium_score': 50,
            'sugar_score': 50
        }

    def _evaluate_suitability(self, allergen_results: Dict[str, Any],
                             medical_results: Dict[str, Any], 
                             dietary_results: Dict[str, Any],
                             health_score: int) -> bool:
        """Uygunluk değerlendirmesi"""
        # Kritik uyarılar varsa uygun değil
        critical_allergens = any(alert.get('severity') == 'critical' 
                               for alert in allergen_results.get('alerts', []))
        critical_medical = any(alert.get('severity') == 'critical' 
                             for alert in medical_results.get('alerts', []))
        
        if critical_allergens or critical_medical:
            return False
        
        # Sağlık skoru çok düşükse uygun değil
        if health_score < 30:
            return False
        
        return True

    def _combine_warnings(self, allergen_results: Dict[str, Any],
                         medical_results: Dict[str, Any], 
                         dietary_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Uyarıları birleştir"""
        warnings = []
        
        # Alerjen uyarıları
        warnings.extend(allergen_results.get('alerts', []))
        
        # Tıbbi uyarılar
        warnings.extend(medical_results.get('alerts', []))
        
        # Diyet uyarıları
        if 'alerts' in dietary_results:
            warnings.extend(dietary_results['alerts'])
        elif not dietary_results.get('is_compliant', True):
            warnings.append({
                'type': 'dietary',
                'severity': 'medium',
                'message': 'Diyet tercihlerinize uygun değil',
                'source': 'dietary_analyzer'
            })
        
        return warnings

    def _calculate_confidence_score(self, product_data: Dict[str, Any], 
                                  user_profile: Dict[str, Any]) -> int:
        """Analiz güven skoru hesapla"""
        confidence = 70
        
        # Ürün verisi kalitesi
        if product_data.get('ingredients'):
            confidence += 10
        if product_data.get('nutrition_facts'):
            confidence += 10
        if product_data.get('allergens'):
            confidence += 5
        
        # Kullanıcı profili kalitesi
        if user_profile.get('allergies'):
            confidence += 5
        if user_profile.get('health_conditions'):
            confidence += 5
        if user_profile.get('dietary_preferences'):
            confidence += 5
        
        return min(100, confidence)

    def _create_error_response(self, error_message: str) -> RuleBasedAnalysisResult:
        """Hata durumu için varsayılan sonuç"""
        return RuleBasedAnalysisResult(
            health_score=0,
            is_suitable=False,
            warnings=[{
                'type': 'error',
                'severity': 'critical',
                'message': error_message,
                'source': 'analyzer'
            }],
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
        """Analiz zamanı"""
        return datetime.now().isoformat()

# Singleton instance
product_analyzer = ProductAnalyzer()