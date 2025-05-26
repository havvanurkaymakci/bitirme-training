import React from 'react';

function AllergyWarnings({ product, userProfile, onWarningGenerated }) {
  
  const checkAllergies = () => {
    const warnings = [];
    
    if (!userProfile.allergies || !product.allergens_tags) return warnings;

    const userAllergies = userProfile.allergies;
    const productAllergens = product.allergens_tags.map(tag => tag.replace('en:', '').toLowerCase());

    userAllergies.forEach(allergy => {
      const allergyKeywords = getAllergyKeywords(allergy);
      
      allergyKeywords.forEach(keyword => {
        const hasAllergen = productAllergens.some(allergen => 
          allergen.includes(keyword) || 
          (product.ingredients_text && product.ingredients_text.toLowerCase().includes(keyword))
        );

        if (hasAllergen) {
          warnings.push({
            type: 'allergy',
            severity: 'critical',
            title: '⚠️ ALERJİ UYARISI',
            message: `Bu ürün ${getAllergyDisplayName(allergy)} içermektedir. Alerjiniz varsa tüketmeyiniz!`,
            details: `Tespit edilen alerjen: ${keyword}`
          });
        }
      });
    });

    return warnings;
  };

  const getAllergyKeywords = (allergy) => {
    const allergyMap = {
      'peanuts': ['yer fıstığı', 'peanut'],
      'tree_nuts': ['badem', 'ceviz', 'fındık', 'nut'],
      'milk': ['süt', 'milk', 'laktoz'],
      'eggs': ['yumurta', 'egg'],
      'wheat': ['buğday', 'wheat'],
      'soy': ['soya', 'soy'],
      'fish': ['balık', 'fish'],
      'shellfish': ['karides', 'midye', 'shellfish'],
      'sesame': ['susam', 'sesame'],
      'corn': ['mısır', 'corn']
    };
    return allergyMap[allergy] || [allergy];
  };

  const getAllergyDisplayName = (allergy) => {
    const displayNames = {
      'peanuts': 'yer fıstığı',
      'tree_nuts': 'sert kabuklu meyveler',
      'milk': 'süt',
      'eggs': 'yumurta',
      'wheat': 'buğday',
      'soy': 'soya',
      'fish': 'balık',
      'shellfish': 'kabuklu deniz ürünleri',
      'sesame': 'susam',
      'corn': 'mısır'
    };
    return displayNames[allergy] || allergy;
  };

  // Component mount olduğunda uyarıları oluştur ve parent'a gönder
  React.useEffect(() => {
    const warnings = checkAllergies();
    if (onWarningGenerated && warnings.length > 0) {
      onWarningGenerated(warnings, 'allergy');
    }
  }, [product, userProfile, onWarningGenerated]);

  // Bu component sadece logic sağlar, render etmez
  return null;
}

export default AllergyWarnings;