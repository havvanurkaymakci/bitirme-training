//NutritionalRecommendations.js
import React, { useState, useEffect } from 'react';

function NutritionalRecommendations({ 
  product, 
  userProfile, 
  onWarningGenerated, 
  onRecommendationGenerated,
  apiBaseUrl = '/api/products',
  authToken 
}) {
  const [loading, setLoading] = useState(false);
  const [healthAnalysis, setHealthAnalysis] = useState(null);
  const [personalizedScore, setPersonalizedScore] = useState(null);
  const [error, setError] = useState(null);

  // API isteği için headers
  const getHeaders = () => ({
    'Content-Type': 'application/json',
    'Authorization': authToken ? `Bearer ${authToken}` : '',
  });

  // Backend'den sağlık analizi al
  const fetchHealthAnalysis = async (productCode) => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(
        `${apiBaseUrl}/health-analysis/${productCode}/`,
        {
          method: 'GET',
          headers: getHeaders(),
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setHealthAnalysis(data);
      
      // Backend'den gelen verileri component'in mevcut formatına dönüştür
      processBackendData(data);
      
    } catch (err) {
      console.error('Health analysis fetch error:', err);
      setError(err.message);
      // Hata durumunda lokal analiz yap
      performLocalAnalysis();
    } finally {
      setLoading(false);
    }
  };

  // Kişiselleştirilmiş skor al
  const fetchPersonalizedScore = async (productCode) => {
    try {
      const response = await fetch(
        `${apiBaseUrl}/personalized-score/`,
        {
          method: 'POST',
          headers: getHeaders(),
          body: JSON.stringify({
            product_code: productCode
          }),
        }
      );

      if (response.ok) {
        const data = await response.json();
        setPersonalizedScore(data);
      }
    } catch (err) {
      console.error('Personalized score fetch error:', err);
    }
  };

  // Backend verisini işle ve mevcut callback'lere uygun formata dönüştür
  const processBackendData = (analysisData) => {
    const warnings = [];
    const recommendations = [];

    // Backend'den gelen negatif noktaları uyarılara çevir
    if (analysisData.negative_points) {
      analysisData.negative_points.forEach(point => {
        warnings.push({
          type: 'nutrition',
          severity: point.severity || 'medium',
          title: point.point || point.category?.toUpperCase() + ' UYARISI',
          message: point.description || point.point,
          details: point.description || '',
          source: 'backend_analysis'
        });
      });
    }

    // Backend'den gelen pozitif noktaları önerilere çevir
    if (analysisData.positive_points) {
      analysisData.positive_points.forEach(point => {
        recommendations.push({
          type: 'nutrition',
          title: point.point || point.category?.toUpperCase() + ' ÖNERİSİ',
          message: point.description || point.point,
          details: point.description || '',
          source: 'backend_analysis'
        });
      });
    }

    // Backend'den gelen önerileri ekle
    if (analysisData.recommendations) {
      analysisData.recommendations.forEach(rec => {
        recommendations.push({
          type: 'nutrition',
          title: '💡 BESLENME ÖNERİSİ',
          message: typeof rec === 'string' ? rec : rec.message || rec.title,
          details: typeof rec === 'object' ? rec.details || rec.description : '',
          source: 'backend_recommendations'
        });
      });
    }

    // Sağlık uyarılarını ekle
    if (analysisData.health_alerts) {
      analysisData.health_alerts.forEach(alert => {
        warnings.push({
          type: 'health',
          severity: alert.severity || 'high',
          title: '⚠️ SAĞLIK UYARISI',
          message: alert.message || alert.title,
          details: alert.details || alert.description || '',
          source: 'health_alerts'
        });
      });
    }

    // Allerjen uyarılarını ekle
    if (analysisData.allergen_alerts && analysisData.allergen_alerts.length > 0) {
      analysisData.allergen_alerts.forEach(allergen => {
        warnings.push({
          type: 'allergen',
          severity: 'high',
          title: '🚨 ALLERJEN UYARISI',
          message: `Bu ürün ${allergen} içermektedir.`,
          details: 'Allerji durumunuz varsa tüketmeyiniz.',
          source: 'allergen_alerts'
        });
      });
    }

    // Tıbbi uyarıları ekle
    if (analysisData.medical_alerts && analysisData.medical_alerts.length > 0) {
      analysisData.medical_alerts.forEach(alert => {
        warnings.push({
          type: 'medical',
          severity: 'high',
          title: '🏥 TIBBİ UYARISI',
          message: alert.message || alert.title,
          details: alert.details || alert.description || '',
          source: 'medical_alerts'
        });
      });
    }

    // Beslenme analizi varsa detayları ekle
    if (analysisData.nutritional_analysis) {
      processNutritionalAnalysis(analysisData.nutritional_analysis, warnings, recommendations);
    }

    // Skor bazlı öneriler
    if (analysisData.personalized_score && analysisData.score_level) {
      const scoreLevel = analysisData.score_level;
      if (scoreLevel.level === 'poor' || scoreLevel.level === 'very_poor') {
        recommendations.push({
          type: 'nutrition',
          title: '📊 SKOR ÖNERİSİ',
          message: `Bu ürün skor açısından ${scoreLevel.description.toLowerCase()}. Daha sağlıklı alternatifler araştırabilirsiniz.`,
          details: `Kişiselleştirilmiş skorunuz: ${analysisData.personalized_score.toFixed(1)}/10`,
          source: 'score_analysis'
        });
      } else if (scoreLevel.level === 'excellent' || scoreLevel.level === 'good') {
        recommendations.push({
          type: 'nutrition',
          title: '⭐ KALİTE ÖNERİSİ',
          message: `Bu ürün skor açısından ${scoreLevel.description.toLowerCase()}. Sağlıklı bir tercih.`,
          details: `Kişiselleştirilmiş skorunuz: ${analysisData.personalized_score.toFixed(1)}/10`,
          source: 'score_analysis'
        });
      }
    }

    // Callback'leri çağır
    if (onWarningGenerated && warnings.length > 0) {
      warnings.forEach(warning => onWarningGenerated(warning));
    }
    
    if (onRecommendationGenerated && recommendations.length > 0) {
      recommendations.forEach(recommendation => onRecommendationGenerated(recommendation));
    }
  };

  // Beslenme analizini işle
  const processNutritionalAnalysis = (nutritionalAnalysis, warnings, recommendations) => {
    const healthMarkers = nutritionalAnalysis.health_markers || {};
    
    // Sağlık belirteçlerine göre uyarı ve öneriler
    if (healthMarkers.high_sugar) {
      warnings.push({
        type: 'nutrition',
        severity: 'medium',
        title: '🍯 YÜKSEK ŞEKER UYARISI',
        message: 'Bu ürün yüksek şeker içermektedir.',
        details: 'Kan şekeri dengenizi etkileyebilir. Porsiyon kontrolü yapın.',
        source: 'nutritional_analysis'
      });
    }

    if (healthMarkers.high_sodium) {
      warnings.push({
        type: 'nutrition',
        severity: 'medium',
        title: '🧂 YÜKSEK SODYUM UYARISI',
        message: 'Bu ürün yüksek sodyum içermektedir.',
        details: 'Tansiyon problemleriniz varsa dikkatli tüketin.',
        source: 'nutritional_analysis'
      });
    }

    if (healthMarkers.high_saturated_fat) {
      warnings.push({
        type: 'nutrition',
        severity: 'medium',
        title: '🧈 DOYMUŞ YAĞ UYARISI',
        message: 'Bu ürün yüksek doymuş yağ içermektedir.',
        details: 'Kolesterol seviyenizı etkileyebilir.',
        source: 'nutritional_analysis'
      });
    }

    if (healthMarkers.good_protein) {
      recommendations.push({
        type: 'nutrition',
        title: '💪 PROTEIN ÖNERİSİ',
        message: 'Bu ürün iyi bir protein kaynağıdır.',
        details: 'Kas gelişimi ve onarımı için faydalıdır.',
        source: 'nutritional_analysis'
      });
    }

    if (healthMarkers.good_fiber) {
      recommendations.push({
        type: 'nutrition',
        title: '🌾 LİF ÖNERİSİ',
        message: 'Bu ürün yüksek lif içermektedir.',
        details: 'Sindirim sağlığınız için faydalıdır.',
        source: 'nutritional_analysis'
      });
    }

    // Kalite değerlendirmesi
    const qualityRating = nutritionalAnalysis.quality_rating;
    if (qualityRating === 'excellent' || qualityRating === 'good') {
      recommendations.push({
        type: 'nutrition',
        title: '⭐ KALİTE ÖNERİSİ',
        message: 'Bu ürün beslenme kalitesi açısından iyidir.',
        details: `Genel kalite değerlendirmesi: ${qualityRating}`,
        source: 'nutritional_analysis'
      });
    }
  };

  // Lokal analiz (backend kullanılamadığında)
  const performLocalAnalysis = () => {
    if (!product || !product.nutriments) return;

    const warnings = [];
    const recommendations = [];
    
    const nutriments = product.nutriments;
    
    // Lokal beslenme kontrolleri (mevcut kod)
    checkLocalNutritionWarnings(nutriments, warnings, recommendations);
    
    // Callback'leri çağır
    if (onWarningGenerated && warnings.length > 0) {
      warnings.forEach(warning => onWarningGenerated(warning));
    }
    
    if (onRecommendationGenerated && recommendations.length > 0) {
      recommendations.forEach(recommendation => onRecommendationGenerated(recommendation));
    }
  };

  // Lokal beslenme uyarıları (fallback)
  const checkLocalNutritionWarnings = (nutriments, warnings, recommendations) => {
    // Yüksek kalori
    if (nutriments.energy_kcal && nutriments.energy_kcal > 500) {
      warnings.push({
        type: 'nutrition',
        severity: 'medium',
        title: '🔥 YÜKSEK KALORİ UYARISI',
        message: `Bu ürün çok yüksek kalorili (${nutriments.energy_kcal} kcal/100g).`,
        details: 'Porsiyon kontrolü yapın.',
        source: 'local_analysis'
      });
    }

    // Yüksek şeker
    if (nutriments.sugars && nutriments.sugars > 20) {
      warnings.push({
        type: 'nutrition',
        severity: 'medium',
        title: '🍯 YÜKSEK ŞEKER UYARISI',
        message: `Bu ürün çok yüksek şeker içermektedir (${nutriments.sugars}g/100g).`,
        details: 'Kan şekeri dengenizi etkileyebilir.',
        source: 'local_analysis'
      });
    }

    // Yüksek tuz
    if (nutriments.salt && nutriments.salt > 2) {
      warnings.push({
        type: 'nutrition',
        severity: 'medium',
        title: '🧂 YÜKSEK TUZ UYARISI',
        message: `Bu ürün çok yüksek tuz içermektedir (${nutriments.salt}g/100g).`,
        details: 'Günlük tuz alımı 5g\'ı geçmemelidir.',
        source: 'local_analysis'
      });
    }

    // Pozitif öneriler
    if (nutriments.fiber && nutriments.fiber > 6) {
      recommendations.push({
        type: 'nutrition',
        title: '✅ BESLENME ÖNERİSİ',
        message: 'Bu ürün yüksek lif içermektedir.',
        details: `Lif içeriği: ${nutriments.fiber}g/100g`,
        source: 'local_analysis'
      });
    }

    if (nutriments.proteins && nutriments.proteins > 10) {
      recommendations.push({
        type: 'nutrition',
        title: '💪 PROTEIN ÖNERİSİ',
        message: 'Bu ürün iyi bir protein kaynağıdır.',
        details: `Protein içeriği: ${nutriments.proteins}g/100g`,
        source: 'local_analysis'
      });
    }
  };

  // Component mount edildiğinde analizleri yap
  useEffect(() => {
    if (!product) return;

    const productCode = product.code || product.product_code || product.id;
    
    if (productCode && authToken) {
      // Backend analizini kullan
      fetchHealthAnalysis(productCode);
      fetchPersonalizedScore(productCode);
    } else {
      // Lokal analizi kullan
      performLocalAnalysis();
    }
  }, [product, userProfile, authToken]);

  // Loading durumunda gösterilecek content
  if (loading) {
    return (
      <div className="nutritional-recommendations-loading">
        <div className="loading-spinner">🔄</div>
        <p>Beslenme analizi yapılıyor...</p>
      </div>
    );
  }

  // Error durumunda gösterilecek content
  if (error && !healthAnalysis) {
    return (
      <div className="nutritional-recommendations-error">
        <div className="error-icon">⚠️</div>
        <p>Analiz yapılırken bir hata oluştu. Temel analiz kullanılıyor.</p>
      </div>
    );
  }

  // Debug bilgileri (development için)
  if (process.env.NODE_ENV === 'development') {
    console.log('NutritionalRecommendations Debug:', {
      healthAnalysis,
      personalizedScore,
      product: product?.code || product?.product_code,
      hasAuthToken: !!authToken
    });
  }

  // Bu component görsel bir şey render etmez, sadis uyarı/öneri üretir
  return null;
}

export default NutritionalRecommendations;