//MedicalWarnings.js
import React from 'react';

function MedicalWarnings({ product, userProfile, onWarningGenerated, onRecommendationGenerated }) {
  
  const checkMedicalConditions = () => {
    const warnings = [];
    const recommendations = [];
    
    if (!userProfile.medical_conditions) return { warnings, recommendations };

    userProfile.medical_conditions.forEach(condition => {
      switch (condition) {
        case 'diabetes_type_1':
        case 'diabetes_type_2':
        case 'prediabetes':
          checkDiabetesWarnings(warnings, recommendations);
          break;
        case 'hypertension':
          checkHypertensionWarnings(warnings, recommendations);
          break;
        case 'high_cholesterol':
          checkCholesterolWarnings(warnings, recommendations);
          break;
        case 'celiac_disease':
          checkCeliacWarnings(warnings, recommendations);
          break;
        case 'heart_disease':
          checkHeartDiseaseWarnings(warnings, recommendations);
          break;
        case 'obesity':
          checkObesityWarnings(warnings, recommendations);
          break;
        case 'chronic_kidney_disease':
          checkKidneyWarnings(warnings, recommendations);
          break;
        default:
          break;
      }
    });

    return { warnings, recommendations };
  };

  const checkDiabetesWarnings = (warnings, recommendations) => {
    const sugars = product.nutriments?.sugars;
    const energy = product.nutriments?.energy_kcal;

    if (sugars && sugars > 15) {
      warnings.push({
        type: 'medical',
        severity: 'high',
        title: '🩺 DİYABET UYARISI',
        message: `Bu ürün yüksek şeker içermektedir (${sugars}g/100g). Kan şekerinizi etkileyebilir.`,
        details: 'Diyabet hastalarının günlük şeker alımını sınırlaması önerilir.'
      });
    }

    if (energy && energy > 400) {
      recommendations.push({
        type: 'medical',
        title: '💡 DİYABET ÖNERİSİ',
        message: 'Yüksek kalorili ürün. Porsiyon kontrolü yapın.',
        details: `Bu ürün 100g başına ${energy} kalori içermektedir.`
      });
    }
  };

  const checkHypertensionWarnings = (warnings, recommendations) => {
    const salt = product.nutriments?.salt;
    const sodium = product.nutriments?.sodium;

    if (salt && salt > 1.5) {
      warnings.push({
        type: 'medical',
        severity: 'high',
        title: '🩺 TANSİYON UYARISI',
        message: `Bu ürün yüksek tuz içermektedir (${salt}g/100g). Tansiyonunuzu etkileyebilir.`,
        details: 'Hipertansiyon hastalarının günlük tuz alımı 5g\'ı geçmemelidir.'
      });
    }

    if (sodium && sodium > 600) {
      warnings.push({
        type: 'medical',
        severity: 'medium',
        title: '🩺 SODYUM UYARISI',
        message: `Bu ürün yüksek sodyum içermektedir (${sodium}mg/100g).`,
        details: 'Sodyum alımınızı sınırlamaya çalışın.'
      });
    }
  };

  const checkCholesterolWarnings = (warnings, recommendations) => {
    const saturatedFat = product.nutriments?.['saturated-fat'];

    if (saturatedFat && saturatedFat > 5) {
      warnings.push({
        type: 'medical',
        severity: 'medium',
        title: '🩺 KOLESTEROL UYARISI',
        message: `Bu ürün yüksek doymuş yağ içermektedir (${saturatedFat}g/100g).`,
        details: 'Yüksek kolesterol hastalarının doymuş yağ alımını sınırlaması önerilir.'
      });
    }
  };

  const checkCeliacWarnings = (warnings, recommendations) => {
    const hasGluten = product.allergens_tags?.some(tag => 
      tag.toLowerCase().includes('gluten') || tag.toLowerCase().includes('wheat')
    ) || product.ingredients_text?.toLowerCase().includes('gluten') ||
       product.ingredients_text?.toLowerCase().includes('buğday');

    if (hasGluten) {
      warnings.push({
        type: 'medical',
        severity: 'critical',
        title: '⚠️ ÇÖLYAK UYARISI',
        message: 'Bu ürün gluten içermektedir. Çölyak hastalarına uygun değildir!',
        details: 'Gluten içeren ürünler çölyak hastalarında bağırsak hasarına neden olabilir.'
      });
    }
  };

  const checkHeartDiseaseWarnings = (warnings, recommendations) => {
    const saturatedFat = product.nutriments?.['saturated-fat'];
    const salt = product.nutriments?.salt;

    if (saturatedFat && saturatedFat > 3) {
      warnings.push({
        type: 'medical',
        severity: 'high',
        title: '🩺 KALP HASTALĞI UYARISI',
        message: `Bu ürün yüksek doymuş yağ içermektedir (${saturatedFat}g/100g).`,
        details: 'Kalp hastalığı olanlar doymuş yağ alımını sınırlamalıdır.'
      });
    }

    if (salt && salt > 1) {
      warnings.push({
        type: 'medical',
        severity: 'medium',
        title: '🩺 KALP HASTALĞI UYARISI',
        message: `Bu ürün orta-yüksek tuz içermektedir (${salt}g/100g).`,
        details: 'Kalp sağlığı için tuz alımını azaltın.'
      });
    }
  };

  const checkObesityWarnings = (warnings, recommendations) => {
    const energy = product.nutriments?.energy_kcal;
    const fat = product.nutriments?.fat;

    if (energy && energy > 450) {
      warnings.push({
        type: 'medical',
        severity: 'medium',
        title: '🩺 OBEZİTE UYARISI',
        message: `Bu ürün yüksek kalorili (${energy} kcal/100g). Kilo kontrolü için dikkatli tüketin.`,
        details: 'Obezite yönetiminde kalori kontrolü önemlidir.'
      });
    }

    if (fat && fat > 20) {
      recommendations.push({
        type: 'medical',
        title: '💡 OBEZİTE ÖNERİSİ',
        message: 'Yüksek yağlı ürün. Porsiyon miktarını azaltın.',
        details: `Bu ürün 100g başına ${fat}g yağ içermektedir.`
      });
    }
  };

  const checkKidneyWarnings = (warnings, recommendations) => {
    const sodium = product.nutriments?.sodium;
    const proteins = product.nutriments?.proteins;

    if (sodium && sodium > 400) {
      warnings.push({
        type: 'medical',
        severity: 'high',
        title: '🩺 BÖBREK HASTALĞI UYARISI',
        message: `Bu ürün yüksek sodyum içermektedir (${sodium}mg/100g).`,
        details: 'Böbrek hastaları sodyum alımını sınırlamalıdır.'
      });
    }

    if (proteins && proteins > 15) {
      recommendations.push({
        type: 'medical',
        title: '💡 BÖBREK HASTALĞI ÖNERİSİ',
        message: 'Yüksek proteinli ürün. Doktorunuzla protein alımınızı görüşün.',
        details: `Bu ürün 100g başına ${proteins}g protein içermektedir.`
      });
    }
  };

  // Component mount olduğunda kontrolleri yap ve parent'a gönder
  React.useEffect(() => {
    const { warnings, recommendations } = checkMedicalConditions();
    
    if (onWarningGenerated && warnings.length > 0) {
      onWarningGenerated(warnings, 'medical');
    }
    
    if (onRecommendationGenerated && recommendations.length > 0) {
      onRecommendationGenerated(recommendations, 'medical');
    }
  }, [product, userProfile, onWarningGenerated, onRecommendationGenerated]);

  // Bu component sadece logic sağlar, render etmez
  return null;
}

export default MedicalWarnings;