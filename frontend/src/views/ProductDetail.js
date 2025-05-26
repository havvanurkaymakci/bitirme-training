import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import axios from 'axios';
import '../styles/ProductDetail.css';


// Uyarı Component'i
const WarningsSection = ({ warnings, onRefreshWarnings, loading }) => {
  const getSeverityIcon = (severity) => {
    switch(severity) {
      case 'critical': return '🚨';
      case 'high': return '⚠️';
      case 'medium': return '⚡';
      case 'low': return 'ℹ️';
      default: return '⚠️';
    }
  };

  const getSeverityText = (severity) => {
    switch(severity) {
      case 'critical': return 'Kritik';
      case 'high': return 'Yüksek';
      case 'medium': return 'Orta';
      case 'low': return 'Düşük';
      default: return 'Bilinmiyor';
    }
  };

  if (!warnings || warnings.length === 0) return null;

  return (
    <div className="warnings-section">
      <div className="section-header">
        <h2>⚠️ Profilinize Özel Uyarılar ({warnings.length})</h2>
        <button 
          onClick={onRefreshWarnings} 
          className="refresh-warnings-button" 
          disabled={loading}
        >
          🔄 Uyarıları Yenile
        </button>
      </div>
      
      {warnings.map((warning, index) => (
        <div key={index} className={`warning-card severity-${warning.severity}`}>
          <div className="warning-header">
            <h3>
              {getSeverityIcon(warning.severity)} {warning.title}
            </h3>
            <span className={`severity-badge ${warning.severity}`}>
              {getSeverityText(warning.severity)}
            </span>
          </div>
          <p className="warning-message">{warning.message}</p>
          {warning.details && (
            <p className="warning-details">{warning.details}</p>
          )}
          {warning.recommendation && (
            <div className="warning-recommendation">
              <strong>💡 Öneri:</strong> {warning.recommendation}
            </div>
          )}
          {warning.affected_conditions && warning.affected_conditions.length > 0 && (
            <div className="affected-conditions">
              <strong>🎯 İlgili durumlar:</strong> {warning.affected_conditions.join(', ')}
            </div>
          )}
        </div>
      ))}
    </div>
  );
};

// Alternatif ürün tıklama işlemi
const handleAlternativeClick = (alternative, onProductSelect) => {
  console.log('🔄 Alternative clicked:', alternative);
  
  if (!onProductSelect) {
    console.error('❌ onProductSelect function not provided');
    alert('Ürün detayı açılamadı. Sayfa yeniden yükleniyor...');
    window.location.reload();
    return;
  }

  try {
    // Backend formatından frontend formatına dönüştür
    const formattedProduct = {
      id: alternative.barcode || alternative.id || `alt_${Date.now()}`,
      product_name: alternative.name || alternative.product_name || 'İsimsiz Ürün',
      product_name: alternative.name || alternative.product_name || 'İsimsiz Ürün',
      brands: alternative.brands || '',
      image_url: alternative.image_url || '',
      nutrition_grade_fr: alternative.nutriscore?.toLowerCase() || '',
      nutriments: alternative.nutrients || alternative.nutriments || {},
      allergens_tags: alternative.allergens || [],
      additives_tags: alternative.additives || [],
      labels_tags: alternative.labels || [],
      categories_tags: alternative.categories || [],
      ingredients_text: alternative.ingredients_text || '',
      nova_group: alternative.nova_group,
      ecoscore_grade: alternative.ecoscore_grade,
      packaging: alternative.packaging || '',
      countries: alternative.countries || ''
    };
    
    console.log('✅ Formatted product for navigation:', formattedProduct);
    onProductSelect(formattedProduct);
    
  } catch (error) {
    console.error('❌ Error handling alternative click:', error);
    alert('Ürün detayına geçerken hata oluştu: ' + error.message);
  }
};

// Öneriler Component'i - Backend veri yapısına göre düzeltilmiş
const RecommendationsSection = ({ recommendations, onProductSelect }) => {
  if (!recommendations || recommendations.length === 0) return null;

  console.log('All recommendations:', recommendations); // Debug

  // Backend'den gelen veriyi incele ve alternatif ürünleri bul
  const alternativeRecommendations = [];
  const otherRecommendations = [];

  recommendations.forEach((rec, index) => {
    console.log(`Recommendation ${index}:`, rec); // Her recommendation'ı logla
    
    // Alternatif ürün kontrolü - birden fazla yol dene
    const hasAlternatives = 
      (rec.alternatives && rec.alternatives.length > 0) ||
      (rec.type === 'alternatives') ||
      (rec.title && rec.title.toLowerCase().includes('alternatif')) ||
      (rec.message && rec.message.toLowerCase().includes('alternatif'));

    if (hasAlternatives) {
      alternativeRecommendations.push(rec);
      console.log('Found alternative recommendation:', rec);
    } else {
      otherRecommendations.push(rec);
    }
  });

  console.log('Separated - Alternatives:', alternativeRecommendations);
  console.log('Separated - Others:', otherRecommendations);

  return (
    <div className="recommendations-section">
      <h2>💡 Size Özel Öneriler ({recommendations.length})</h2>
      
      {/* Debug Bilgisi - sadece development'da göster */}
      {process.env.NODE_ENV === 'development' && (
        <div style={{
          background: '#f8f9fa', 
          border: '1px solid #dee2e6', 
          padding: '10px', 
          margin: '10px 0',
          borderRadius: '5px',
          fontSize: '12px'
        }}>
          <strong>🔍 Debug Info:</strong><br/>
          Total recommendations: {recommendations.length}<br/>
          Alternative recommendations: {alternativeRecommendations.length}<br/>
          Other recommendations: {otherRecommendations.length}
          <details style={{marginTop: '5px'}}>
            <summary>Raw Data</summary>
            <pre style={{fontSize: '10px', maxHeight: '200px', overflow: 'auto'}}>
              {JSON.stringify(recommendations, null, 2)}
            </pre>
          </details>
        </div>
      )}
      
      {/* Diğer öneriler */}
      {otherRecommendations.map((recommendation, index) => (
        <div key={index} className={`recommendation-card ${recommendation.severity || ''}`}>
          <div className="recommendation-header">
            <h3>{recommendation.title}</h3>
            {recommendation.severity && (
              <span className={`severity-badge ${recommendation.severity}`}>
                {recommendation.severity === 'critical' ? '🚨 Kritik' : 
                 recommendation.severity === 'warning' ? '⚠️ Uyarı' : 
                 recommendation.severity === 'info' ? 'ℹ️ Bilgi' : recommendation.severity}
              </span>
            )}
          </div>
          <p className="recommendation-message">{recommendation.message}</p>
          {recommendation.details && (
            <p className="recommendation-details">{recommendation.details}</p>
          )}
          {recommendation.category && (
            <div className="recommendation-category">
              <small>Kategori: {recommendation.category}</small>
            </div>
          )}
        </div>
      ))}

      {/* Alternatif ürün önerileri */}
      {alternativeRecommendations.map((altRec, index) => (
        <div key={`alt-${index}`} className="alternatives-recommendation">
          <div className="recommendation-header">
            <h3>{altRec.title}</h3>
            <span className="info-badge">ℹ️ Alternatif Öneriler</span>
          </div>
          <p className="recommendation-message">{altRec.message}</p>
          
          {/* Alternatif ürünleri göster */}
          {altRec.alternatives && altRec.alternatives.length > 0 ? (
            <div className="embedded-alternatives">
              <h4>🔄 Önerilen Alternatif Ürünler:</h4>
              <div className="alternatives-grid">
                {altRec.alternatives.map((alternative, altIndex) => (
                  <div 
                    key={altIndex} 
                    className="alternative-card clickable" 
                    onClick={() => handleAlternativeClick(alternative, onProductSelect)}
                  >
                    <div className="alternative-image">
                      {alternative.image_url ? (
                        <img 
                          src={alternative.image_url} 
                          alt={alternative.name || alternative.product_name}
                          onError={(e) => {e.target.style.display = 'none'}}
                        />
                      ) : (
                        <div className="no-image">📦</div>
                      )}
                    </div>
                    
                    <div className="alternative-info">
                      <h4 className="alternative-name">
                        {alternative.name || alternative.product_name}
                      </h4>
                      <p className="alternative-brand">
                        {alternative.brands || 'Marka belirtilmemiş'}
                      </p>
                      
                      {/* İyileştirmeler */}
                      {alternative.improvements && alternative.improvements.length > 0 && (
                        <div className="alternative-reasons">
                          <h5>✨ İyileştirmeler:</h5>
                          <ul>
                            {alternative.improvements.map((improvement, impIndex) => (
                              <li key={impIndex}>{improvement}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Sağlık Skoru */}
                      {alternative.health_score && (
                        <div className="score-comparison">
                          <div className="score-item">
                            <span className="score-label">Sağlık Skoru:</span>
                            <span className={`score-value ${alternative.health_score >= 70 ? 'good' : alternative.health_score >= 50 ? 'fair' : 'poor'}`}>
                              {alternative.health_score}/100
                            </span>
                          </div>
                        </div>
                      )}

                      {/* Nutri-Score */}
                      {alternative.nutriscore && (
                        <div className="nutri-score-comparison">
                          <span>Nutri-Score: </span>
                          <span className={`nutri-score grade-${alternative.nutriscore.toLowerCase()}`}>
                            {alternative.nutriscore.toUpperCase()}
                          </span>
                        </div>
                      )}
                      
                      <button className="view-alternative-btn">
                        📋 Detayları Görüntüle
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="no-specific-alternatives">
              <p>🔍 Bu öneri için spesifik alternatif ürün listesi mevcut değil.</p>
              {altRec.details && <p><em>{altRec.details}</em></p>}
            </div>
          )}
        </div>
      ))}

      {/* Hiç alternatif bulunamadı durumu */}
      {alternativeRecommendations.length === 0 && (
        <div className="no-alternatives-info">
          <div className="info-card">
            <h3>🔍 Alternatif Ürün Önerisi</h3>
            <p>Bu ürün için spesifik alternatif ürün önerisi bulunamadı.</p>
            <div className="possible-reasons">
              <h4>Olası nedenler:</h4>
              <ul>
                <li>• OpenFoodFacts veritabanı bağlantı sorunu (timeout)</li>
                <li>• Bu kategoride yeterli alternatif ürün bulunmuyor</li>
                <li>• Ürün zaten profil kriterlerinize uygun</li>
              </ul>
            </div>
            <p><small>💡 Farklı bir ürün deneyebilir veya daha sonra tekrar kontrol edebilirsiniz.</small></p>
          </div>
        </div>
      )}

      {/* Backend Error Durumu - Eğer timeout hatası varsa */}
      <div className="backend-status-info">
        <details>
          <summary>🔧 Teknik Bilgi</summary>
          <p>Alternatif ürün arama servisi OpenFoodFacts API'sinden veri çekmeye çalışıyor. 
          Bazen bu servis yavaş yanıt verebilir veya timeout olabilir.</p>
        </details>
      </div>
    </div>
  );
};

// Beslenme Tavsiyeleri Component'i
const NutritionalAdviceSection = ({ nutritionalAdvice }) => {
  if (!nutritionalAdvice || nutritionalAdvice.length === 0) return null;

  return (
    <div className="nutritional-advice-section">
      <h2>🥗 Kişisel Beslenme Tavsiyeleri</h2>
      {nutritionalAdvice.map((advice, index) => (
        <div key={index} className="advice-card">
          <h3>{advice.title}</h3>
          <p>{advice.message}</p>
          {advice.suggested_alternatives && advice.suggested_alternatives.length > 0 && (
            <div className="alternatives">
              <strong>🔄 Alternatif Öneriler:</strong>
              <ul>
                {advice.suggested_alternatives.map((alt, altIndex) => (
                  <li key={altIndex}>{alt}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      ))}
    </div>
  );
};

// Uygunluk Durumu Component'i
const SuitabilitySection = ({ analysisResult }) => {
  if (!analysisResult) return null;

  return (
    <div className={`suitability-section ${analysisResult.is_suitable ? 'suitable' : 'not-suitable'}`}>
      <h2>
        {analysisResult.is_suitable ? 
          '✅ Bu ürün profilinize uygun görünüyor' : 
          '❌ Bu ürün profilinize uygun değil'}
      </h2>
      {analysisResult.summary && (
        <p className="overall-message">{analysisResult.summary}</p>
      )}
      {analysisResult.detailed_explanation && (
        <div className="detailed-explanation">
          <p>{analysisResult.detailed_explanation}</p>
        </div>
      )}
      {analysisResult.usage_recommendations && (
        <div className="usage-recommendations">
          <strong>📋 Kullanım Önerileri:</strong>
          <p>{analysisResult.usage_recommendations}</p>
        </div>
      )}
    </div>
  );
};

// Başarı Durumu Component'i (Uyarı olmadığında)
const SuccessSection = ({ analysisResult }) => {
  if (!analysisResult || !analysisResult.is_suitable) return null;

  const hasWarnings = analysisResult.warnings && analysisResult.warnings.length > 0;
  const hasRecommendations = analysisResult.recommendations && analysisResult.recommendations.length > 0;

  if (hasWarnings || hasRecommendations) return null;

  return (
    <div className="no-warnings-section">
      <h2>🎉 Mükemmel Uyum!</h2>
      <p>Bu ürün sizin sağlık profilinize tamamen uygun. Herhangi bir uyarı tespit edilmedi.</p>
      {analysisResult.health_score && (
        <div className="excellent-score">
          <p>Kişisel sağlık skorunuz: <strong>{analysisResult.health_score}/100</strong></p>
          <small>Bu skor size özel hesaplanmıştır</small>
        </div>
      )}
    </div>
  );
};

// Analiz Yükleme Component'i
const AnalysisLoading = () => (
  <div className="analysis-loading">
    <div className="loading-spinner"></div>
    <p>🔍 Ürün kişisel profilinize göre analiz ediliyor...</p>
    <small>Bu işlem birkaç saniye sürebilir</small>
  </div>
);

// Analiz Hatası Component'i
const AnalysisError = ({ error, onRetry, onDismiss }) => (
  <div className="analysis-error">
    <h3>❌ Analiz Hatası</h3>
    <p>{error}</p>
    <div className="error-actions">
      <button onClick={onRetry} className="retry-button">
        🔄 Tekrar Dene
      </button>
      <button onClick={onDismiss} className="dismiss-button">
        ✖ Kapat
      </button>
    </div>
  </div>
);

// Ana ProductDetail Component'i
function ProductDetail() {
  const location = useLocation();
  const navigate = useNavigate();

  const [product, setProduct] = useState(() => {
    const stateProduct = location.state?.product;
    if (stateProduct) {
      return stateProduct;
    }
    return null;
  });

  const [userProfile, setUserProfile] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  
  // Backend'den gelen analiz sonuçları için state'ler
  const [analysisResult, setAnalysisResult] = useState(null);
  const [analysisError, setAnalysisError] = useState(null);

  useEffect(() => {
    checkAuthAndLoadProfile();
  }, []);

  useEffect(() => {
    // Kullanıcı profili yüklendikten ve authenticated olduktan sonra analiz yap
    if (isAuthenticated && userProfile && product && !loading) {
      analyzeProduct();
    }
  }, [isAuthenticated, userProfile, product, loading]);

  const checkAuthAndLoadProfile = async () => {
    try {
      const token = localStorage.getItem('authTokens');
      if (!token) {
        setIsAuthenticated(false);
        setLoading(false);
        return;
      }

      const accessToken = JSON.parse(token).access;

      const response = await axios.get('http://localhost:8000/api/profile/', {
        headers: {
          'Authorization': `Bearer ${accessToken}`
        }
      });

      setUserProfile(response.data);
      setIsAuthenticated(true);
    } catch (error) {
      console.error('Profil bilgileri alınamadı:', error);
      if (error.response?.status === 401) {
        localStorage.removeItem('authTokens');
      }
      setIsAuthenticated(false);
    } finally {
      setLoading(false);
    }
  };

  const analyzeProduct = async () => {
    if (!product || !isAuthenticated) return;

    setAnalysisLoading(true);
    setAnalysisError(null);

    try {
      const token = localStorage.getItem('authTokens');
      const accessToken = JSON.parse(token).access;

      // Backend'deki analyze_product_complete endpoint'ini kullan
      const response = await axios.post(
        'http://localhost:8000/api/analyze-product/',
        {
          product_data: {
            // OpenFoodFacts API'sinden gelen ürün verisini düzgün formatta gönder
            id: product.id || product._id,
            product_name: product.product_name,
            brands: product.brands,
            nutriments: product.nutriments || {},
            ingredients_text: product.ingredients_text,
            allergens_tags: product.allergens_tags || [],
            additives_tags: product.additives_tags || [],
            labels_tags: product.labels_tags || [],
            categories_tags: product.categories_tags || [],
            nutrition_grade_fr: product.nutrition_grade_fr,
            nova_group: product.nova_group,
            ecoscore_grade: product.ecoscore_grade,
            packaging: product.packaging,
            countries: product.countries,
            image_url: product.image_url,
            // 100g başına değerleri ekle
            nutriments_100g: {
              energy_kcal: product.nutriments?.['energy-kcal_100g'] || product.nutriments?.energy_kcal,
              fat: product.nutriments?.fat_100g || product.nutriments?.fat,
              'saturated-fat': product.nutriments?.['saturated-fat_100g'] || product.nutriments?.['saturated-fat'],
              sugars: product.nutriments?.sugars_100g || product.nutriments?.sugars,
              salt: product.nutriments?.salt_100g || product.nutriments?.salt,
              sodium: product.nutriments?.sodium_100g || product.nutriments?.sodium,
              proteins: product.nutriments?.proteins_100g || product.nutriments?.proteins,
              fiber: product.nutriments?.fiber_100g || product.nutriments?.fiber,
              carbohydrates: product.nutriments?.carbohydrates_100g || product.nutriments?.carbohydrates
            }
          }
        },
        {
          headers: {
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/json'
          }
        }
      );

      console.log('Analiz sonucu:', response.data); // Debug için
      setAnalysisResult(response.data);
      
    } catch (error) {
      console.error('Ürün analizi hatası:', error);
      setAnalysisError(
        error.response?.data?.error || 
        'Ürün analizi sırasında bir hata oluştu. Lütfen tekrar deneyin.'
      );
    } finally {
      setAnalysisLoading(false);
    }
  };

  const getWarningsOnly = async () => {
    if (!product || !isAuthenticated) return;

    setAnalysisLoading(true);
    setAnalysisError(null);

    try {
      const token = localStorage.getItem('authTokens');
      const accessToken = JSON.parse(token).access;

      const response = await axios.post(
        'http://localhost:8000/api/product-warnings/',
        {
          product_data: {
            id: product.id || product._id,
            product_name: product.product_name,
            brands: product.brands,
            nutriments: product.nutriments || {},
            ingredients_text: product.ingredients_text,
            allergens_tags: product.allergens_tags || [],
            additives_tags: product.additives_tags || [],
            labels_tags: product.labels_tags || [],
            categories_tags: product.categories_tags || [],
            nutrition_grade_fr: product.nutrition_grade_fr,
            nova_group: product.nova_group
          }
        },
        {
          headers: {
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/json'
          }
        }
      );

      // Sadece uyarıları güncelle
      setAnalysisResult(prev => ({
        ...prev,
        warnings: response.data.warnings || [],
        allergen_analysis: {
          ...prev?.allergen_analysis,
          alerts: response.data.allergen_alerts || []
        },
        medical_analysis: {
          ...prev?.medical_analysis,
          alerts: response.data.medical_alerts || []
        }
      }));
      
    } catch (error) {
      console.error('Uyarı analizi hatası:', error);
      setAnalysisError(
        error.response?.data?.error || 
        'Uyarı analizi sırasında bir hata oluştu'
      );
    } finally {
      setAnalysisLoading(false);
    }
  };

  // Alternatif ürün seçildiğinde - güncellenmiş format
  const handleAlternativeProductSelect = (alternativeProduct) => {
    // Yeni ürünle sayfayı güncelle
    setProduct(alternativeProduct);
    setAnalysisResult(null); // Önceki analizi temizle
    
    // Yeni ürün için analiz yap
    if (isAuthenticated && userProfile) {
      setTimeout(() => {
        analyzeProduct();
      }, 100);
    }
    
    // Sayfanın üstüne scroll yap
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleLoginRedirect = () => {
    navigate('/login', {
      state: {
        from: location,
        returnUrl: '/product-detail',
        productData: product
      }
    });
  };

  const handleBackToSearch = () => {
    navigate('/product-search');
  };

  // Uyarıları severity'ye göre sırala ve birleştir
  const getSortedWarnings = () => {
    if (!analysisResult) return [];
    
    const allWarnings = [
      ...(analysisResult.warnings || []),
      ...(analysisResult.allergen_analysis?.alerts || []),
      ...(analysisResult.medical_analysis?.alerts || [])
    ];

    return allWarnings.sort((a, b) => {
      const severityOrder = { 'critical': 0, 'high': 1, 'medium': 2, 'low': 3 };
      return (severityOrder[a.severity] || 4) - (severityOrder[b.severity] || 4);
    });
  };

  const getHealthScoreColor = (score) => {
    if (score >= 80) return 'excellent';
    if (score >= 60) return 'good';
    if (score >= 40) return 'fair';
    return 'poor';
  };

  // Profil bilgilerini göster
  const renderUserProfileInfo = () => {
    if (!userProfile) return null;

    return (
      <div className="user-profile-info">
        <h3>👤 Profil Bilgileriniz</h3>
        <div className="profile-details">
          {userProfile.allergies && userProfile.allergies.length > 0 && (
            <div className="profile-item">
              <strong>Alerjiler:</strong> {userProfile.allergies.join(', ')}
            </div>
          )}
          {userProfile.dietary_preferences && userProfile.dietary_preferences.length > 0 && (
            <div className="profile-item">
              <strong>Diyet Tercihleri:</strong> {userProfile.dietary_preferences.join(', ')}
            </div>
          )}
          {userProfile.medical_conditions && userProfile.medical_conditions.length > 0 && (
            <div className="profile-item">
              <strong>Sağlık Durumu:</strong> {userProfile.medical_conditions.join(', ')}
            </div>
          )}
          {userProfile.health_goals && userProfile.health_goals.length > 0 && (
            <div className="profile-item">
              <strong>Sağlık Hedefleri:</strong> {userProfile.health_goals.join(', ')}
            </div>
          )}
        </div>
      </div>
    );
  };

  if (!product) {
    return (
      <div className="product-detail-container">
        <div className="error-message">
          <h2>Ürün bulunamadı</h2>
          <p>Ürün bilgileri yüklenemedi. Lütfen arama sayfasından bir ürün seçin.</p>
          <button onClick={handleBackToSearch} className="back-button">
            Arama Sayfasına Dön
          </button>
        </div>
      </div>
    );
  }

  const sortedWarnings = getSortedWarnings();

  return (
    <div className="product-detail-container">
      <div className="product-detail-header">
        <button onClick={handleBackToSearch} className="back-button">
          ← Arama Sayfasına Dön
        </button>
      </div>

      <div className="product-detail-content">
        {/* Ürün Temel Bilgileri */}
        <div className="product-basic-info">
          <div className="product-image-section">
            {product.image_url && (
              <img 
                src={product.image_url} 
                alt={product.product_name}
                className="product-detail-image"
                onError={(e) => {
                  e.target.style.display = 'none';
                }}
              />
            )}
          </div>
          
          <div className="product-info-section">
            <h1 className="product-title">{product.product_name || 'İsim yok'}</h1>
            
            <div className="product-meta">
              <p><strong>Marka:</strong> {product.brands || 'Belirtilmemiş'}</p>
              <p><strong>Ülke:</strong> {product.countries || 'Belirtilmemiş'}</p>
              <p><strong>Ambalaj:</strong> {product.packaging || 'Belirtilmemiş'}</p>
              <p><strong>Nutri-Score:</strong> 
                <span className={`nutri-score grade-${product.nutrition_grade_fr?.toLowerCase()}`}>
                  {product.nutrition_grade_fr?.toUpperCase() || 'Bilinmiyor'}
                </span>
              </p>
              
              {product.nova_group && (
                <p><strong>NOVA Grubu:</strong> 
                  <span className={`nova-group nova-${product.nova_group}`}>{product.nova_group}</span>
                </p>
              )}
              
              {/* Sağlık Skoru - Backend'den gelen */}
              {analysisResult?.health_score !== undefined && (
                <div className="health-score-section">
                  <p><strong>Kişisel Sağlık Skoru:</strong> 
                    <span className={`health-score ${getHealthScoreColor(analysisResult.health_score)}`}>
                      {analysisResult.health_score}/100
                    </span>
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Besin Değerleri */}
        <div className="nutrition-section">
          <h2>Besin Değerleri (100g başına)</h2>
          <div className="nutrition-grid">
            <div className="nutrition-item">
              <span className="nutrition-label">Enerji:</span>
              <span className="nutrition-value">
                {product.nutriments?.['energy-kcal_100g'] || product.nutriments?.energy_kcal ? 
                  `${product.nutriments?.['energy-kcal_100g'] || product.nutriments?.energy_kcal} kcal` : 
                  'Veri yok'}
              </span>
            </div>
            <div className="nutrition-item">
              <span className="nutrition-label">Yağ:</span>
              <span className="nutrition-value">
                {product.nutriments?.fat_100g || product.nutriments?.fat ? 
                  `${product.nutriments?.fat_100g || product.nutriments?.fat}g` : 
                  'Veri yok'}
              </span>
            </div>
            <div className="nutrition-item">
              <span className="nutrition-label">Doymuş Yağ:</span>
              <span className="nutrition-value">
                {product.nutriments?.['saturated-fat_100g'] || product.nutriments?.['saturated-fat'] ? 
                  `${product.nutriments?.['saturated-fat_100g'] || product.nutriments?.['saturated-fat']}g` : 
                  'Veri yok'}
              </span>
            </div>
            <div className="nutrition-item">
              <span className="nutrition-label">Şeker:</span>
              <span className="nutrition-value">
                {product.nutriments?.sugars_100g || product.nutriments?.sugars ? 
                  `${product.nutriments?.sugars_100g || product.nutriments?.sugars}g` : 
                  'Veri yok'}
              </span>
            </div>
            <div className="nutrition-item">
              <span className="nutrition-label">Tuz:</span>
              <span className="nutrition-value">
                {product.nutriments?.salt_100g || product.nutriments?.salt ? 
                  `${product.nutriments?.salt_100g || product.nutriments?.salt}g` : 
                  'Veri yok'}
              </span>
            </div>
            <div className="nutrition-item">
              <span className="nutrition-label">Protein:</span>
              <span className="nutrition-value">
                {product.nutriments?.proteins_100g || product.nutriments?.proteins ? 
                  `${product.nutriments?.proteins_100g || product.nutriments?.proteins}g` : 
                  'Veri yok'}
              </span>
            </div>
            <div className="nutrition-item">
              <span className="nutrition-label">Lif:</span>
              <span className="nutrition-value">
                {product.nutriments?.fiber_100g || product.nutriments?.fiber ? 
                  `${product.nutriments?.fiber_100g || product.nutriments?.fiber}g` : 
                  'Veri yok'}
              </span>
            </div>
            <div className="nutrition-item">
              <span className="nutrition-label">Sodyum:</span>
              <span className="nutrition-value">
                {product.nutriments?.sodium_100g || product.nutriments?.sodium ? 
                  `${(product.nutriments?.sodium_100g || product.nutriments?.sodium) * 1000}mg` : 
                  'Veri yok'}
              </span>
            </div>
          </div>
        </div>
 
        {/* İçerikler */}
        <div className="ingredients-section">
          <h2>İçerikler</h2>
          <p className="ingredients-text">
            {product.ingredients_text || 'İçerik bilgisi mevcut değil'}
          </p>
          
          {product.allergens_tags && product.allergens_tags.length > 0 && (
            <div className="allergens-section">
              <h3>🚨 Alerjenler</h3>
              <div className="allergens-list">
                {product.allergens_tags.map((allergen, index) => (
                  <span key={index} className="allergen-tag">
                    {allergen.replace('en:', '').replace(/-/g, ' ')}
                  </span>
                ))}
              </div>
            </div>
          )}

          {product.additives_tags && product.additives_tags.length > 0 && (
            <div className="additives-section">
              <h3>⚗️ Katkı Maddeleri</h3>
              <div className="additives-list">
                {product.additives_tags.map((additive, index) => (
                  <span key={index} className="additive-tag">
                    {additive.replace('en:', '').replace(/-/g, ' ')}
                  </span>
                ))}
              </div>
            </div>
          )}

          {product.labels_tags && product.labels_tags.length > 0 && (
            <div className="labels-section">
              <h3>🏷️ Etiketler</h3>
              <div className="labels-list">
                {product.labels_tags.map((label, index) => (
                  <span key={index} className="label-tag">
                    {label.replace('en:', '').replace(/-/g, ' ')}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Kişiselleştirilmiş Analiz Bölümü */}
        {loading ? (
          <div className="loading-section">
            <p>👤 Kullanıcı bilgileri yükleniyor...</p>
          </div>
        ) : !isAuthenticated ? (
          <div className="auth-required-section">
            <h2>🔒 Kişiselleştirilmiş Analiz</h2>
            <p>Bu ürünle ilgili size özel uyarılar, öneriler ve sağlık skoru görmek için giriş yapmanız gerekmektedir.</p>
            <ul>
              <li>✅ Alerjilerinize göre ürün uygunluğu</li>
              <li>✅ Sağlık durumunuza özel tavsiyeleri</li>
              <li>✅ Diyet tercihlerinize uygun analiz</li>
              <li>✅ Kişisel sağlık skoru</li>
            </ul>
            <button onClick={handleLoginRedirect} className="login-button">
              🚀 Giriş Yap ve Analiz Et
            </button>
          </div>
        ) : (
          <div className="recommendations-container">
            {/* Kullanıcı Profil Bilgileri */}
            {renderUserProfileInfo()}

            {/* Analiz Yükleniyor */}
            {analysisLoading && <AnalysisLoading />}

            {/* Analiz Hatası */}
            {analysisError && (
              <AnalysisError 
                error={analysisError}
                onRetry={analyzeProduct}
                onDismiss={() => setAnalysisError(null)}
              />
            )}

            {/* Analiz Sonuçları */}
            {analysisResult && !analysisLoading && (
              <>
                {/* Genel Uygunluk Durumu */}
                <SuitabilitySection analysisResult={analysisResult} />

                {/* Uyarılar */}
                <WarningsSection 
                  warnings={sortedWarnings}
                  onRefreshWarnings={getWarningsOnly}
                  loading={analysisLoading}
                />

                {/* Öneriler */}
                <RecommendationsSection recommendations={analysisResult.recommendations} />



                {/* Beslenme Tavsiyeleri */}
                <NutritionalAdviceSection nutritionalAdvice={analysisResult.nutritional_advice} />

                {/* Hiç uyarı yok durumu */}
                <SuccessSection analysisResult={analysisResult} />

                {/* Analiz Detayları */}
                {analysisResult.analysis_timestamp && (
                  <div className="analysis-info">
                    <small>
                      📅 Analiz tarihi: {new Date(analysisResult.analysis_timestamp).toLocaleString('tr-TR')}
                    </small>
                  </div>
                )}

                {/* Yeniden Analiz Butonu */}
                <div className="analysis-actions">
                  <button onClick={analyzeProduct} className="reanalyze-button" disabled={analysisLoading}>
                    {analysisLoading ? '🔄 Analiz ediliyor...' : '🔄 Yeniden Analiz Et'}
                  </button>
                  <small>Profilinizi güncellediyseniz yeniden analiz edebilirsiniz</small>
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default ProductDetail;