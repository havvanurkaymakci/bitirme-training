
//NutritionalRecommendations.js
import React from 'react';

function NutritionalRecommendations({ product, userProfile, onWarningGenerated, onRecommendationGenerated }) {
  
  const checkNutritionalRecommendations = () => {
    const warnings = [];
    const recommendations = [];
    
    const fiber = product.nutriments?.fiber;
    const proteins = product.nutriments?.proteins;
    const nutriScore = product.nutrition_grade_fr;

    // Pozitif beslenme önerileri
    if (fiber && fiber > 6) {
      recommendations.push({
        type: 'nutrition',
        title: '✅ BESLENME ÖNERİSİ',
        message: 'Bu ürün yüksek lif içermektedir. Sindirim sağlığınız için faydalıdır.',
        details: `Lif içeriği: ${fiber}g/100g`
      });
    }

    if (proteins && proteins > 10) {
      recommendations.push({
        type: 'nutrition',
        title: '💪 PROTEIN ÖNERİSİ',
        message: 'Bu ürün iyi bir protein kaynağıdır.',
        details: `Protein içeriği: ${proteins}g/100g`
      });
    }

    // Nutri-Score değerlendirmesi
    if (nutriScore && (nutriScore === 'a' || nutriScore === 'b')) {
      recommendations.push({
        type: 'nutrition',
        title: '⭐ KALİTE ÖNERİSİ',
        message: 'Bu ürün Nutri-Score değerlendirmesinde iyi puan almıştır.',
        details: `Nutri-Score: ${nutriScore.toUpperCase()}`
      });
    } else if (nutriScore && (nutriScore === 'd' || nutriScore === 'e')) {
      warnings.push({
        type: 'nutrition',
        severity: 'low',
        title: '📊 NUTRİ-SCORE UYARISI',
        message: 'Bu ürün Nutri-Score değerlendirmesinde düşük puan almıştır.',
        details: `Nutri-Score: ${nutriScore.toUpperCase()}`
      });
    }

    // Genel beslenme uyarıları
    checkGeneralNutritionWarnings(warnings, recommendations);

    return { warnings, recommendations };
  };

  const checkGeneralNutritionWarnings = (warnings, recommendations) => {
    const energy = product.nutriments?.energy_kcal;
    const fat = product.nutriments?.fat;
    const saturatedFat = product.nutriments?.['saturated-fat'];
    const sugars = product.nutriments?.sugars;
    const salt = product.nutriments?.salt;
    const fiber = product.nutriments?.fiber;

    // Yüksek kalori uyarısı
    if (energy && energy > 500) {
      warnings.push({
        type: 'nutrition',
        severity: 'medium',
        title: '🔥 YÜKSEK KALORİ UYARISI',
        message: `Bu ürün çok yüksek kalorili (${energy} kcal/100g). Porsiyon kontrolü yapın.`,
        details: 'Günlük kalori alımınızı aşmamak için dikkatli olun.'
      });
    }

    // Yüksek yağ uyarısı
    if (fat && fat > 25) {
      warnings.push({
        type: 'nutrition',
        severity: 'medium',
        title: '🧈 YÜKSEK YAĞ UYARISI',
        message: `Bu ürün yüksek yağ içermektedir (${fat}g/100g).`,
        details: 'Yüksek yağlı ürünleri sınırlı miktarda tüketin.'
      });
    }

    // Yüksek doymuş yağ uyarısı
    if (saturatedFat && saturatedFat > 5) {
      warnings.push({
        type: 'nutrition',
        severity: 'medium',
        title: '🧈 DOYMUŞ YAĞ UYARISI',
        message: `Bu ürün yüksek doymuş yağ içermektedir (${saturatedFat}g/100g).`,
        details: 'Doymuş yağ alımını günlük kalorinin %10\'undan az tutun.'
      });
    }

    // Yüksek şeker uyarısı
    if (sugars && sugars > 20) {
      warnings.push({
        type: 'nutrition',
        severity: 'medium',
        title: '🍯 YÜKSEK ŞEKER UYARISI',
        message: `Bu ürün çok yüksek şeker içermektedir (${sugars}g/100g).`,
        details: 'Yüksek şeker alımı obezite ve diş çürümesi riskini artırır.'
      });
    }

    // Yüksek tuz uyarısı
    if (salt && salt > 2) {
      warnings.push({
        type: 'nutrition',
        severity: 'medium',
        title: '🧂 YÜKSEK TUZ UYARISI',
        message: `Bu ürün çok yüksek tuz içermektedir (${salt}g/100g).`,
        details: 'Günlük tuz alımı 5g\'ı geçmemelidir.'
      });
    }

    // Düşük lif uyarısı (eğer karbonhidrat kaynağıysa)
    const carbs = product.nutriments?.carbohydrates;
    if (carbs && carbs > 20 && (!fiber || fiber < 3)) {
      recommendations.push({
        type: 'nutrition',
        title: '🌾 LİF ÖNERİSİ',
        message: 'Bu ürün karbonhidrat açısından zengin ancak lif içeriği düşük.',
        details: 'Daha yüksek lifli alternatifler tercih edebilirsiniz.'
      });
    }

    // Pozitif vitamin/mineral önerileri
    checkVitaminMineralContent(recommendations);
  };

  const checkVitaminMineralContent = (recommendations) => {
    // Eğer ürün vitamin/mineral bilgisi varsa önerilerde belirt
    const nutriments = product.nutriments || {};
    
    // Kalsiyum kontrolü
    if (nutriments.calcium && nutriments.calcium > 100) {
      recommendations.push({
        type: 'nutrition',
        title: '🦴 KALSİYUM ÖNERİSİ',
        message: 'Bu ürün kalsiyum açısından zengindir. Kemik sağlığınız için faydalıdır.',
        details: `Kalsiyum içeriği: ${nutriments.calcium}mg/100g`
      });
    }

    // Demir kontrolü
    if (nutriments.iron && nutriments.iron > 2) {
      recommendations.push({
        type: 'nutrition',
        title: '🩸 DEMİR ÖNERİSİ',
        message: 'Bu ürün demir açısından zengindir. Kan sağlığınız için faydalıdır.',
        details: `Demir içeriği: ${nutriments.iron}mg/100g`
      });
    }

    // Magnezyum kontrolü
    if (nutriments.magnesium && nutriments.magnesium > 50) {
      recommendations.push({
        type: 'nutrition',
        title: '⚡ MAGNEZYUM ÖNERİSİ',
        message: 'Bu ürün magnezyum açısından zengindir. Kas ve sinir fonksiyonları için faydalıdır.',
        details: `Magnezyum içeriği: ${nutriments.magnesium}mg/100g`
      });
    }

    // Potasyum kontrolü
    if (nutriments.potassium && nutriments.potassium > 300) {
      recommendations.push({
        type: 'nutrition',
        title: '💧 POTASYUM ÖNERİSİ',
        message: 'Bu ürün potasyum açısından zengindir. Kalp sağlığı ve kan basıncı için faydalıdır.',
        details: `Potasyum içeriği: ${nutriments.potassium}mg/100g`
      });
    }

    // Vitamin C kontrolü
    if (nutriments['vitamin-c'] && nutriments['vitamin-c'] > 10) {
      recommendations.push({
        type: 'nutrition',
        title: '🍊 VİTAMİN C ÖNERİSİ',
        message: 'Bu ürün C vitamini açısından zengindir. Bağışıklık sisteminiz için faydalıdır.',
        details: `Vitamin C içeriği: ${nutriments['vitamin-c']}mg/100g`
      });
    }

    // Vitamin D kontrolü
    if (nutriments['vitamin-d'] && nutriments['vitamin-d'] > 1) {
      recommendations.push({
        type: 'nutrition',
        title: '☀️ VİTAMİN D ÖNERİSİ',
        message: 'Bu ürün D vitamini içermektedir. Kemik sağlığı ve bağışıklık sistemi için önemlidir.',
        details: `Vitamin D içeriği: ${nutriments['vitamin-d']}μg/100g`
      });
    }

    // Omega-3 kontrolü
    if (nutriments['omega-3-fat'] && nutriments['omega-3-fat'] > 0.5) {
      recommendations.push({
        type: 'nutrition',
        title: '🐟 OMEGA-3 ÖNERİSİ',
        message: 'Bu ürün Omega-3 yağ asitleri içermektedir. Kalp ve beyin sağlığı için faydalıdır.',
        details: `Omega-3 içeriği: ${nutriments['omega-3-fat']}g/100g`
      });
    }
  };

  // Component mount edildiğinde kontrolleri yap
  React.useEffect(() => {
    const { warnings, recommendations } = checkNutritionalRecommendations();
    
    // Callback fonksiyonları varsa çağır
    if (onWarningGenerated && warnings.length > 0) {
      warnings.forEach(warning => onWarningGenerated(warning));
    }
    
    if (onRecommendationGenerated && recommendations.length > 0) {
      recommendations.forEach(recommendation => onRecommendationGenerated(recommendation));
    }
  }, [product, userProfile, onWarningGenerated, onRecommendationGenerated]);

  // Bu component görsel bir şey render etmez, sadece uyarı/öneri üretir
  return null;
}

export default NutritionalRecommendations;