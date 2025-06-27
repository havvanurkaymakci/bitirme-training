import '../styles/ComprehensiveProductInfo.css';
import React, { useState } from 'react';

const ComprehensiveProductInfo = ({ product, analysisResult }) => {
  const [activeTab, setActiveTab] = useState('overview');

  // Utility functions
  const getHealthScoreColor = (score) => {
    if (score >= 80) return 'high';
    if (score >= 60) return 'medium';
    if (score >= 40) return 'medium';
    return 'low';
  };

  const getNutriScoreGrade = (grade) => {
    return `grade-${grade?.toLowerCase()}` || 'grade-unknown';
  };

  const getNovaGroupClass = (group) => {
    return `nova-${group}` || 'nova-unknown';
  };

  const getAdditivesCountClass = (count) => {
    if (count > 10) return 'high';
    if (count > 5) return 'medium';
    return 'low';
  };

  const getSummaryStatClass = (value, thresholds) => {
    if (value > thresholds.high) return 'high';
    if (value > thresholds.medium) return 'medium';
    return 'low';
  };

  // Format functions
  const formatAllergens = (allergens) => {
    if (!allergens || allergens.length === 0) return [];
    
    return allergens.map(allergen => {
      return allergen
        .replace('en:', '')
        .replace(/-/g, ' ')
        .split(' ')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
    });
  };

  const formatAdditives = (additives) => {
    if (!additives || additives.length === 0) return [];
    
    return additives.map(additive => {
      return additive
        .replace('en:', '')
        .replace(/-/g, ' ')
        .replace(/e\d+/gi, match => match.toUpperCase())
        .split(' ')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
    });
  };

  const formatLabels = (labels) => {
    if (!labels || labels.length === 0) return [];
    
    return labels.map(label => {
      return label
        .replace('en:', '')
        .replace(/-/g, ' ')
        .split(' ')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
    });
  };

  const getNutrientValue = (nutrient) => {
    if (!product.nutriments && !product.nutritional_summary) return null;
    
    const nutrients = product.nutriments || product.nutritional_summary || {};
    
    const variations = {
      energy_kcal: ['energy-kcal_100g', 'energy_kcal', 'energy-kcal', 'energy'],
      fat: ['fat_100g', 'fat'],
      saturated_fat: ['saturated-fat_100g', 'saturated-fat', 'saturated_fat'],
      sugars: ['sugars_100g', 'sugars'],
      salt: ['salt_100g', 'salt'],
      sodium: ['sodium_100g', 'sodium'],
      proteins: ['proteins_100g', 'proteins', 'protein'],
      fiber: ['fiber_100g', 'fiber', 'fibre'],
      carbohydrates: ['carbohydrates_100g', 'carbohydrates']
    };

    const possibleKeys = variations[nutrient] || [nutrient];
    
    for (const key of possibleKeys) {
      if (nutrients[key] !== undefined && nutrients[key] !== null) {
        return nutrients[key];
      }
    }
    
    return null;
  };

  const formatNutrientDisplay = (value, unit = 'g') => {
    if (value === null || value === undefined) return 'Veri yok';
    
    const numValue = parseFloat(value);
    if (isNaN(numValue)) return 'Veri yok';
    
    if (unit === 'mg' && numValue < 1) {
      return `${(numValue * 1000).toFixed(1)}mg`;
    }
    
    return `${numValue.toFixed(1)}${unit}`;
  };

  // Data preparation
  const allergens = formatAllergens(product.allergens_tags || product.allergens);
  const additives = formatAdditives(product.additives_tags || product.additives);
  const labels = formatLabels(product.labels_tags || product.labels);

  const nutritionData = [
    { label: 'Enerji', value: formatNutrientDisplay(getNutrientValue('energy_kcal'), ' kcal'), icon: '⚡' },
    { label: 'Yağ', value: formatNutrientDisplay(getNutrientValue('fat'), 'g'), icon: '🥑' },
    { label: 'Doymuş Yağ', value: formatNutrientDisplay(getNutrientValue('saturated_fat'), 'g'), icon: '🧈' },
    { label: 'Karbonhidrat', value: formatNutrientDisplay(getNutrientValue('carbohydrates'), 'g'), icon: '🌾' },
    { label: 'Şeker', value: formatNutrientDisplay(getNutrientValue('sugars'), 'g'), icon: '🍯' },
    { label: 'Protein', value: formatNutrientDisplay(getNutrientValue('proteins'), 'g'), icon: '💪' },
    { label: 'Lif', value: formatNutrientDisplay(getNutrientValue('fiber'), 'g'), icon: '🌿' },
    { label: 'Tuz', value: formatNutrientDisplay(getNutrientValue('salt'), 'g'), icon: '🧂' }
  ];

  return (
    <div className="comprehensive-product-container">
      {/* Header Section */}
      <div className="product-header">
        <div className="product-header-content">
          {/* Product Image */}
          <div className="product-image-container">
            {product.image_url ? (
              <img 
                src={product.image_url} 
                alt={product.product_name}
                className="product-detail-image"
                onError={(e) => {
                  e.target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgdmlld0JveD0iMCAwIDIwMCAyMDAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIyMDAiIGhlaWdodD0iMjAwIiBmaWxsPSIjRjNGNEY2Ii8+CjxwYXRoIGQ9Ik01MCA2MEwxNTAgMTYwTTUwIDE2MEwxNTAgNjAiIHN0cm9rZT0iI0Q1RDlERCIgc3Ryb2tlLXdpZHRoPSIyIi8+Cjx0ZXh0IHg9IjEwMCIgeT0iMTEwIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmaWxsPSIjOUI5QkExIiBmb250LXNpemU9IjE0Ij5SZXNpbSBZb2s8L3RleHQ+Cjwvc3ZnPg==';
                }}
              />
            ) : (
              <div className="product-image-placeholder">
                📦
              </div>
            )}
          </div>

                    {/* Product Info */}
            <div className="product-info-main">
            <h1 className="product-title">{product.product_name || 'İsim yok'}</h1>
            
            <div className="product-meta-grid">
                <div className="product-meta-section">
                <p className="product-meta-item">
                    <span>Marka:</span> {product.brands || product.main_brand || 'Belirtilmemiş'}
                </p>
                <p className="product-meta-item">
                    <span>Kategori:</span> {product.main_category || 'Belirtilmemiş'}
                </p>
                <p className="product-meta-item">
                    <span>Ülke:</span> {product.countries || 'Belirtilmemiş'}
                </p>
                </div>
                
                <div className="product-meta-section">
                <p className="product-meta-item">
                    <span>Ambalaj:</span> {product.packaging || 'Belirtilmemiş'}
                </p>
                {product.quantity && (
                    <p className="product-meta-item">
                    <span>Miktar:</span> {product.quantity}
                    </p>
                )}
                {product.serving_size && (
                    <p className="product-meta-item">
                    <span>Porsiyon:</span> {product.serving_size}
                    </p>
                )}
                </div>
            </div>

            {/* Scores - sadece varsa göster */}
            {((product.nutrition_grade_fr || product.nutriscore_grade) || 
                (product.nova_group || product.processing_level) || 
                (analysisResult?.personalized_score !== undefined)) && (
                <div className="product-scores">
                {(product.nutrition_grade_fr || product.nutriscore_grade) && (
                    <div className="score-item">
                    <span className="score-label">Nutri-Score:</span>
                    <span className={`nutri-score ${getNutriScoreGrade(product.nutrition_grade_fr || product.nutriscore_grade)}`}>
                        {(product.nutrition_grade_fr || product.nutriscore_grade)?.toUpperCase()}
                    </span>
                    </div>
                )}
                
                {(product.nova_group || product.processing_level) && (
                    <div className="score-item">
                    <span className="score-label">İşlenme:</span>
                    <span className={`nova-score ${getNovaGroupClass(product.nova_group || product.processing_level)}`}>
                        {product.nova_group === 1 && 'Doğal/Az İşlenmiş'}
                        {product.nova_group === 2 && 'İşlenmiş Mutfak Malzemesi'}
                        {product.nova_group === 3 && 'İşlenmiş Gıda'}
                        {product.nova_group === 4 && 'Ultra İşlenmiş Gıda'}
                        {!product.nova_group && 'Bilinmiyor'}
                    </span>
                    </div>
                )}
                
                {analysisResult?.personalized_score !== undefined && (
                    <div className="score-item">
                    <span className="score-label">Kişisel Skor:</span>
                    <span className={`health-score ${getHealthScoreColor(analysisResult.personalized_score * 10)}`}>
                        {analysisResult.personalized_score}/10
                    </span>
                    </div>
                )}
                </div>
            )}
            </div>
          </div>
        </div>

      {/* Navigation Tabs */}
      <div className="product-tabs">
        {[
          { id: 'overview', label: 'Genel Bakış', icon: '📊' },
          { id: 'nutrition', label: 'Besin Değerleri', icon: '🥗' },
          { id: 'ingredients', label: 'İçerikler', icon: '📝' },
          { id: 'additives', label: 'Katkı Maddeleri', icon: '⚗️' }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`tab-button ${activeTab === tab.id ? 'active' : ''}`}
          >
            <span className="tab-icon">{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content Area */}
      <div className="tab-content">
        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="overview-content">
            {/* Quick Stats */}
            <div className="quick-stats">
              <div className="stat-card naturalness">
                <div className="stat-card-content">
                  <div className="stat-icon green">
                    🌿
                  </div>
                  <div className="stat-info green">
                    <h3>Doğallık</h3>
                    <p>
                      {additives.length === 0 ? 'Katkısız' : `${additives.length} katkı maddesi`}
                    </p>
                  </div>
                </div>
              </div>

              <div className="stat-card allergens">
                <div className="stat-card-content">
                  <div className="stat-icon orange">
                    ⚠️
                  </div>
                  <div className="stat-info orange">
                    <h3>Alerjenler</h3>
                    <p>
                      {allergens.length === 0 ? 'Tespit edilmedi' : `${allergens.length} alerjen`}
                    </p>
                  </div>
                </div>
              </div>

              <div className="stat-card certifications">
                <div className="stat-card-content">
                  <div className="stat-icon blue">
                    🏷️
                  </div>
                  <div className="stat-info blue">
                    <h3>Sertifikalar</h3>
                    <p>
                      {labels.length === 0 ? 'Yok' : `${labels.length} etiket`}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Labels */}
            {labels.length > 0 && (
              <div className="labels-section">
                <h3>🏷️ Özellikler & Sertifikalar</h3>
                <div className="labels-grid">
                  {labels.map((label, index) => (
                    <span key={index} className="label-tag">
                      {label}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Nutrition Tab */}
        {activeTab === 'nutrition' && (
          <div className="nutrition-content">
            <h3>🥗 Besin Değerleri (100g başına)</h3>
            
            <div className="nutrition-grid">
              {nutritionData.map((nutrient, index) => (
                <div key={index} className="nutrition-card">
                  <div className="nutrition-card-header">
                    <span className="nutrition-icon">{nutrient.icon}</span>
                    <span className="nutrition-label">{nutrient.label}</span>
                  </div>
                  <div className="nutrition-value">{nutrient.value}</div>
                </div>
              ))}
            </div>

            {/* Macro Ratios */}
            {product.macro_ratios && (
              <div className="macro-ratios">
                <h4>📊 Makro Besin Oranları</h4>
                <div className="macro-list">
                  {[
                    { name: 'Protein', ratio: product.macro_ratios.protein_ratio, class: 'protein' },
                    { name: 'Karbonhidrat', ratio: product.macro_ratios.carb_ratio, class: 'carbs' },
                    { name: 'Yağ', ratio: product.macro_ratios.fat_ratio, class: 'fat' }
                  ].map((macro, index) => (
                    <div key={index} className="macro-item">
                      <div className="macro-name">{macro.name}</div>
                      <div className="macro-bar-container">
                        <div 
                          className={`macro-bar ${macro.class}`}
                          style={{width: `${macro.ratio || 0}%`}}
                        ></div>
                      </div>
                      <div className="macro-percentage">
                        {macro.ratio?.toFixed(1) || 0}%
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Ingredients Tab */}
        {activeTab === 'ingredients' && (
          <div className="ingredients-content">
            <h3>📝 İçerikler</h3>
            
            {/* Ingredients Text */}
            <div className="ingredients-text-card">
              <h4>İçerik Listesi</h4>
              <p className="ingredients-text">
                {product.ingredients_text || product.ingredients || 'İçerik bilgisi mevcut değil'}
              </p>
            </div>

            {/* Allergens */}
            {allergens.length > 0 && (
              <div className="allergens-card">
                <h4>🚨 Alerjenler</h4>
                <div className="allergens-list">
                  {allergens.map((allergen, index) => (
                    <span key={index} className="allergen-tag">
                      {allergen}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Categories */}
            {(product.categories_tags || product.categories) && (
              <div className="categories-section">
                <h4>📂 Kategoriler</h4>
                <div className="categories-list">
                  {(product.categories_tags || product.categories || []).slice(0, 10).map((category, index) => (
                    <span key={index} className="category-tag">
                      {category.replace('en:', '').replace(/-/g, ' ')}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Additives Tab */}
        {activeTab === 'additives' && (
          <div className="additives-content">
            <h3>⚗️ Katkı Maddeleri</h3>
            
            {additives.length > 0 ? (
              <>
                <div className="additives-summary">
                  <div className="additives-summary-header">
                    <div className={`additives-count ${getAdditivesCountClass(additives.length)}`}>
                      {additives.length}
                    </div>
                    <h4>
                      Toplam {additives.length} katkı maddesi tespit edildi
                    </h4>
                  </div>
                  
                  {additives.length > 5 && (
                    <p className="additives-warning">
                      ⚠️ Bu ürün yüksek miktarda katkı maddesi içermektedir.
                    </p>
                  )}
                </div>

                <div className="additives-grid">
                  {additives.map((additive, index) => (
                    <div key={index} className="additive-item">
                      <span className="additive-name">{additive}</span>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="no-additives-card">
                <div className="no-additives-icon">
                  ✅
                </div>
                <h4>Katkı Maddesi Yok</h4>
                <p>Bu ürün herhangi bir katkı maddesi içermemektedir.</p>
              </div>
            )}

            {/* Processing Level Summary */}
            <div className="product-summary">
              <h4>📊 Ürün Özellikleri Özeti</h4>
              <div className="summary-stats">
                <div className="summary-stat">
                  <div className={`summary-stat-value ${getSummaryStatClass(product.processing_level || product.nova_group || 0, {high: 3, medium: 2})}`}>
                    {product.processing_level || product.nova_group || 'N/A'}
                  </div>
                  <div className="summary-stat-label">İşlenme Seviyesi</div>
                </div>
                <div className="summary-stat">
                  <div className={`summary-stat-value ${getSummaryStatClass(additives.length, {high: 5, medium: 2})}`}>
                    {additives.length}
                  </div>
                  <div className="summary-stat-label">Katkı Maddesi</div>
                </div>
                <div className="summary-stat">
                  <div className={`summary-stat-value ${getSummaryStatClass(allergens.length, {high: 3, medium: 1})}`}>
                    {allergens.length}
                  </div>
                  <div className="summary-stat-label">Alerjen</div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ComprehensiveProductInfo;