
import React from 'react';

function DietaryWarnings({ product, userProfile, onWarningGenerated, onRecommendationGenerated }) {
  
  const checkDietaryPreferences = () => {
    const warnings = [];
    const recommendations = [];
    
    if (!userProfile.dietary_preferences) return { warnings, recommendations };

    userProfile.dietary_preferences.forEach(preference => {
      switch (preference) {
        case 'vegan':
          checkVeganCompatibility(warnings, recommendations);
          break;
        case 'vegetarian':
          checkVegetarianCompatibility(warnings, recommendations);
          break;
        case 'gluten_free':
          checkGlutenFreeCompatibility(warnings, recommendations);
          break;
        case 'lactose_free':
          checkLactoseFreeCompatibility(warnings, recommendations);
          break;
        case 'ketogenic':
          checkKetoCompatibility(warnings, recommendations);
          break;
        case 'low_carb':
          checkLowCarbCompatibility(warnings, recommendations);
          break;
        case 'halal':
          checkHalalCompatibility(warnings, recommendations);
          break;
        default:
          break;
      }
    });

    return { warnings, recommendations };
  };

  const checkVeganCompatibility = (warnings, recommendations) => {
    const nonVeganIngredients = ['süt', 'yumurta', 'bal', 'et', 'tavuk', 'balık', 'peynir', 'tereyağı'];
    const ingredientsText = product.ingredients_text?.toLowerCase() || '';
    
    const foundNonVegan = nonVeganIngredients.find(ingredient => 
      ingredientsText.includes(ingredient)
    );

    if (foundNonVegan) {
      warnings.push({
        type: 'dietary',
        severity: 'medium',
        title: '🌱 VEGAN DİYET UYARISI',
        message: 'Bu ürün vegan diyetinize uygun olmayabilir.',
        details: `Tespit edilen hayvansal ürün: ${foundNonVegan}`
      });
    }
  };

  const checkVegetarianCompatibility = (warnings, recommendations) => {
    const nonVegetarianIngredients = ['et', 'tavuk', 'balık', 'dana', 'kuzu'];
    const ingredientsText = product.ingredients_text?.toLowerCase() || '';
    
    const foundNonVegetarian = nonVegetarianIngredients.find(ingredient => 
      ingredientsText.includes(ingredient)
    );

    if (foundNonVegetarian) {
      warnings.push({
        type: 'dietary',
        severity: 'medium',
        title: '🥬 VEJETARYEN DİYET UYARISI',
        message: 'Bu ürün vejetaryen diyetinize uygun değildir.',
        details: `Tespit edilen et ürünü: ${foundNonVegetarian}`
      });
    }
  };

  const checkGlutenFreeCompatibility = (warnings, recommendations) => {
    const glutenIngredients = ['buğday', 'arpa', 'çavdar', 'gluten'];
    const ingredientsText = product.ingredients_text?.toLowerCase() || '';
    
    const foundGluten = glutenIngredients.find(ingredient => 
      ingredientsText.includes(ingredient)
    );

    if (foundGluten) {
      warnings.push({
        type: 'dietary',
        severity: 'high',
        title: '🌾 GLÜTENSIZ DİYET UYARISI',
        message: 'Bu ürün glütensiz diyetinize uygun değildir.',
        details: `Tespit edilen gluten kaynağı: ${foundGluten}`
      });
    }
  };

  const checkLactoseFreeCompatibility = (warnings, recommendations) => {
    const lactoseIngredients = ['süt', 'laktoz', 'peynir', 'yoğurt', 'tereyağı', 'krema'];
    const ingredientsText = product.ingredients_text?.toLowerCase() || '';
    
    const foundLactose = lactoseIngredients.find(ingredient => 
      ingredientsText.includes(ingredient)
    );

    if (foundLactose) {
      warnings.push({
        type: 'dietary',
        severity: 'medium',
        title: '🥛 LAKTOZSUZ DİYET UYARISI',
        message: 'Bu ürün laktozsuz diyetinize uygun olmayabilir.',
        details: `Tespit edilen laktoz kaynağı: ${foundLactose}`
      });
    }
  };

  const checkKetoCompatibility = (warnings, recommendations) => {
    const sugars = product.nutriments?.sugars;
    const carbs = product.nutriments?.carbohydrates;

    if (sugars && sugars > 5) {
      warnings.push({
        type: 'dietary',
        severity: 'high',
        title: '🥓 KETO DİYET UYARISI',
        message: `Bu ürün yüksek şeker içermektedir (${sugars}g/100g). Keto diyetinize uygun değildir.`,
        details: 'Keto diyetinde günlük karbonhidrat alımı çok düşük tutulmalıdır.'
      });
    }

    if (carbs && carbs > 10) {
      warnings.push({
        type: 'dietary',
        severity: 'medium',
        title: '🥓 KETO DİYET UYARISI',
        message: `Bu ürün yüksek karbonhidrat içermektedir (${carbs}g/100g).`,
        details: 'Keto diyetinde karbonhidrat alımını sınırlayın.'
      });
    }
  };

  const checkLowCarbCompatibility = (warnings, recommendations) => {
    const carbs = product.nutriments?.carbohydrates;
    const sugars = product.nutriments?.sugars;

    if (carbs && carbs > 20) {
      warnings.push({
        type: 'dietary',
        severity: 'medium',
        title: '🍞 DÜŞÜK KARBONHIDRAT DİYET UYARISI',
        message: `Bu ürün yüksek karbonhidrat içermektedir (${carbs}g/100g).`,
        details: 'Düşük karbonhidrat diyetinde karbonhidrat alımını sınırlayın.'
      });
    }

    if (sugars && sugars > 10) {
      warnings.push({
        type: 'dietary',
        severity: 'medium',
        title: '🍞 DÜŞÜK KARBONHIDRAT DİYET UYARISI',
        message: `Bu ürün yüksek şeker içermektedir (${sugars}g/100g).`,
        details: 'Düşük karbonhidrat diyetinde şeker alımını minimize edin.'
      });
    }
  };

  const checkHalalCompatibility = (warnings, recommendations) => {
    const nonHalalIngredients = ['domuz', 'alkol', 'şarap', 'bira', 'jelatin'];
    const ingredientsText = product.ingredients_text?.toLowerCase() || '';
    
    const foundNonHalal = nonHalalIngredients.find(ingredient => 
      ingredientsText.includes(ingredient)
    );

    if (foundNonHalal) {
      warnings.push({
        type: 'dietary',
        severity: 'high',
        title: '☪️ HELAL DİYET UYARISI',
        message: 'Bu ürün helal diyetinize uygun olmayabilir.',
        details: `Tespit edilen şüpheli içerik: ${foundNonHalal}`
      });
    }

    // Jelatin kontrolü - çoğunlukla domuz kaynaklıdır
    if (ingredientsText.includes('jelatin') && !ingredientsText.includes('bitkisel jelatin')) {
      warnings.push({
        type: 'dietary',
        severity: 'medium',
        title: '☪️ HELAL DİYET UYARISI',
        message: 'Bu ürün jelatin içermektedir. Kaynağını kontrol ediniz.',
        details: 'Jelatin genellikle domuz kaynaklıdır, helal sertifikası olup olmadığını kontrol edin.'
      });
    }
  };

  // Component mount olduğunda kontrolleri yap ve parent'a gönder
  React.useEffect(() => {
    const { warnings, recommendations } = checkDietaryPreferences();
    
    if (onWarningGenerated && warnings.length > 0) {
      onWarningGenerated(warnings, 'dietary');
    }
    
    if (onRecommendationGenerated && recommendations.length > 0) {
      onRecommendationGenerated(recommendations, 'dietary');
    }
  }, [product, userProfile, onWarningGenerated, onRecommendationGenerated]);

  // Bu component sadece logic sağlar, render etmez
  return null;
}

export default DietaryWarnings;