import React, { useState, useEffect } from 'react';
import '../styles/PersonalizedRecommendations.css';

const PersonalizedRecommendations = ({ 
  product, 
  isAuthenticated,
  userProfile,
  onProductClick,
  showAlternatives = true,
  showSimilar = true,
  autoLoad = true,
  axiosInstance, // useAxios instance from parent
  useMLEndpoint = true // Use new ML endpoints
}) => {
  // ✅ DEBUG: Props kontrolü
  console.log('🔍 PersonalizedRecommendations Props:', {
    product: product ? 'Product exists' : 'Product is null/undefined',
    productName: product?.product_name || product?.name || 'No name',
    productCode: product?.product_code || product?.code || product?.id,
    isAuthenticated,
    userProfile: userProfile ? 'Profile exists' : 'No profile',
    showAlternatives,
    showSimilar,
    autoLoad,
    useMLEndpoint
  });

  const [recommendations, setRecommendations] = useState([]);
  const [alternatives, setAlternatives] = useState([]);
  const [personalizedScore, setPersonalizedScore] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('alternatives');

  useEffect(() => {
    if (isAuthenticated && product && userProfile && autoLoad && axiosInstance) {
      loadRecommendations();
    }
  }, [isAuthenticated, product, userProfile, autoLoad, axiosInstance]);

  // ✅ Backend API URLs - Updated for new structure
  const getApiUrl = (endpoint) => {
    return `/products/${endpoint}`;
  };

  // ✅ UPDATED: Load recommendations using new ML endpoints
  const loadRecommendations = async () => {
    if (!product || !isAuthenticated || !userProfile || !axiosInstance) return;

    setLoading(true);
    setError(null);

    try {
      const productCode = product.product_code || product.code || product.id;
      if (!productCode) {
        console.warn('Product code not found');
        setError('Ürün kodu bulunamadı');
        return;
      }
      
      const promises = [];

      // 1. ✅ ML-based alternatives (product-specific) - Updated API call
      if (showAlternatives) {
        promises.push(
          axiosInstance.get(getApiUrl('ml-recommendations/'), {
            params: {
              product_code: productCode,
              limit: 5,
              min_score: 6.0
            }
          }).then(response => ({type: 'alternatives', data: response.data}))
        );
      }

      // 2. ✅ ML-based general recommendations - Updated API call
      if (showSimilar) {
        const categories = product.main_category || product.categories || product.category || '';
        promises.push(
          axiosInstance.get(getApiUrl('ml-recommendations/'), {
            params: {
              limit: 6,
              categories: categories,
              min_score: 6.0
            }
          }).then(response => ({type: 'recommendations', data: response.data}))
        );
      }
      
      // 3. ✅ Personalized score - Updated API call
      promises.push(
        axiosInstance.get(getApiUrl('personalized-score/'), {
          params: {
            product_code: productCode
          }
        }).then(response => ({type: 'score', data: response.data}))
      );

      const results = await Promise.allSettled(promises);

      results.forEach((result, index) => {
        if (result.status === 'fulfilled') {
          const { type, data } = result.value;
          
          switch(type) {
            case 'alternatives':
              // ✅ Handle new backend response structure
              if (data.type === 'alternatives' && data.alternatives) {
                setAlternatives(data.alternatives);
                console.log('✅ Alternatives loaded:', data.alternatives.length);
              } else if (data.type === 'personalized' && data.recommendations) {
                // If general recommendations returned, use as alternatives
                setAlternatives(data.recommendations);
                console.log('✅ Alternatives (from general) loaded:', data.recommendations.length);
              }
              break;
              
            case 'recommendations':
              // ✅ Handle new backend response structure
              if (data.type === 'personalized' && data.recommendations) {
                setRecommendations(data.recommendations);
                console.log('✅ Recommendations loaded:', data.recommendations.length);
              } else if (data.type === 'alternatives' && data.alternatives) {
                // If alternatives returned, use as recommendations
                setRecommendations(data.alternatives);
                console.log('✅ Recommendations (from alternatives) loaded:', data.alternatives.length);
              }
              break;
              
            case 'score':
              setPersonalizedScore(data);
              console.log('✅ Personalized score loaded:', data);
              break;
          }
        } else {
          const errorTypes = ['alternatives', 'recommendations', 'score'];
          const errorType = errorTypes[Math.min(index, errorTypes.length - 1)];
          console.error(`❌ ${errorType} loading error:`, result.reason?.response?.data || result.reason?.message);
        }
      });
      
    } catch (error) {
      console.error('❌ Recommendations loading error:', error);
      setError(
        error.response?.data?.error || 
        error.response?.data?.message ||
        error.message ||
        'Öneriler yüklenirken hata oluştu'
      );
    } finally {
      setLoading(false);
    }
  };

  // ✅ Updated product comparison - using axiosInstance
  const compareProducts = async (productCodes) => {
    if (!isAuthenticated || productCodes.length < 2 || !axiosInstance) return;

    try {
      const response = await axiosInstance.post(getApiUrl('compare/'), {
        product_codes: productCodes
      });

      console.log('✅ Comparison result:', response.data);
      return response.data;
    } catch (error) {
      console.error('❌ Comparison error:', error);
      return null;
    }
  };

  // Health score color determination
  const getHealthScoreColor = (score) => {
    const normalizedScore = score <= 10 ? score * 10 : score;
    
    if (normalizedScore >= 80) return 'excellent';
    if (normalizedScore >= 60) return 'good';
    if (normalizedScore >= 40) return 'moderate';
    if (normalizedScore >= 20) return 'poor';
    return 'very-poor';
  };

  // ✅ Updated product card render - Compatible with new backend response structure
  const renderProductCard = (product, index, isAlternative = false) => {
    const productCode = product.product_code || product.code || product.id;
    
    return (
      <div 
        key={`${productCode}-${index}`} 
        className={`product-card ${isAlternative ? 'alternative-card' : 'recommendation-card'}`}
        onClick={() => onProductClick && onProductClick(product)}
      >
        <div className="product-image">
          {product.image_url ? (
            <img 
              src={product.image_url} 
              alt={product.product_name || product.name}
              onError={(e) => {
                e.target.style.display = 'none';
                e.target.nextSibling.style.display = 'block';
              }}
            />
          ) : null}
          <div className="no-image-placeholder" style={{display: product.image_url ? 'none' : 'block'}}>
            📦
          </div>
        </div>
        
        <div className="product-info">
          <h4 className="product-name">{product.product_name || product.name}</h4>
          <p className="product-brand">{product.brands || product.brand}</p>
          
          {/* ✅ Updated score handling for new backend response */}
          {(product.final_score || product.ml_score || product.personalized_score || product.target_score) && (
            <div className={`health-score ${getHealthScoreColor(
              product.final_score || product.ml_score || product.personalized_score || product.target_score
            )}`}>
              <span className="score-value">
                {Math.round((
                  product.final_score || product.ml_score || product.personalized_score || product.target_score
                ) <= 10 ? 
                  (product.final_score || product.ml_score || product.personalized_score || product.target_score) * 10 : 
                  (product.final_score || product.ml_score || product.personalized_score || product.target_score)
                )}/100
              </span>
              <span className="score-label">Size Uygunluk</span>
            </div>
          )}
          
          {/* ✅ Updated reason handling for new backend response */}
          {(product.reason || product.recommendation_reason) && (
            <div className="match-reasons">
              <small>
                💡 {product.reason || product.recommendation_reason}
              </small>
            </div>
          )}
          
          {/* ✅ Health benefits for recommendations */}
          {!isAlternative && product.health_benefits && Array.isArray(product.health_benefits) && (
            <div className="health-benefits">
              <small>
                🌱 Faydalar: {product.health_benefits.slice(0, 2).join(', ')}
                {product.health_benefits.length > 2 && '...'}
              </small>
            </div>
          )}
          
          {/* ✅ Score improvement for alternatives */}
          {isAlternative && product.score_improvement && (
            <div className="improvement-areas">
              <small>
                ✨ İyileştirme: +{Math.round(product.score_improvement * 10)} puan
              </small>
            </div>
          )}
          
          <div className="product-badges">
            {(product.nutrition_grade_fr || product.nutriscore_grade) && (
              <span className={`nutri-score grade-${(product.nutrition_grade_fr || product.nutriscore_grade)}`}>
                Nutri-Score {(product.nutrition_grade_fr || product.nutriscore_grade).toUpperCase()}
              </span>
            )}
            {product.nova_group && (
              <span className={`nova-group nova-${product.nova_group}`}>
                NOVA {product.nova_group}
              </span>
            )}
          </div>
        </div>
        
        <div className="product-actions">
          <button 
            className="view-details-button"
            onClick={(e) => {
              e.stopPropagation();
              onProductClick && onProductClick(product);
            }}
          >
            🔍 Detaylar
          </button>
          <button 
            className="compare-button"
            onClick={(e) => {
              e.stopPropagation();
              const currentProductCode = product?.product_code || product?.code || product?.id;
              compareProducts([
                currentProductCode,
                productCode
              ]);
            }}
          >
            ⚖️ Karşılaştır
          </button>
        </div>
      </div>
    );
  };

  // Loading Component
  const LoadingComponent = () => (
    <div className="recommendations-loading">
      <div className="loading-spinner"></div>
      <p>🎯 Sizin için özel öneriler hazırlanıyor...</p>
      <small>Bu işlem birkaç saniye sürebilir</small>
    </div>
  );

  // Error Component
  const ErrorComponent = ({ error, onRetry }) => (
    <div className="recommendations-error">
      <h3>❌ Öneriler Yüklenemedi</h3>
      <p>{error}</p>
      <div className="error-actions">
        <button onClick={onRetry} className="retry-button">
          🔄 Tekrar Dene
        </button>
        <button onClick={() => setError(null)} className="dismiss-button">
          ✖ Kapat
        </button>
      </div>
    </div>
  );

  // ✅ Updated Personalized Score Section - Compatible with new backend response
  const PersonalizedScoreSection = () => {
    if (!personalizedScore) return null;

    const score = personalizedScore.personalized_score || personalizedScore.score;
    const normalizedScore = score <= 10 ? score * 10 : score;

    return (
      <div className="personalized-score-section">
        <h3>📊 Kişisel Uygunluk Skoru</h3>
        <div className="score-display">
          <div className={`main-score ${getHealthScoreColor(score)}`}>
            <span className="score-number">{Math.round(normalizedScore)}</span>
            <span className="score-total">/100</span>
          </div>
          <div className="score-explanation">
            <p>Bu ürün sizin profilinize <strong>{Math.round(normalizedScore)}%</strong> uygun.</p>
            
            {/* ✅ Updated analysis handling for new backend response */}
            {personalizedScore.analysis && (
              <div className="match-reasons-detailed">
                <h4>🎯 Uygunluk Nedenleri:</h4>
                {personalizedScore.analysis.health_match_reasons && (
                  <ul>
                    {personalizedScore.analysis.health_match_reasons.map((reason, index) => (
                      <li key={index}>{reason}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        </div>
        
        {/* ✅ Updated score breakdown for new backend response */}
        {personalizedScore.score_level && (
          <div className="score-breakdown">
            <h4>📈 Detaylı Değerlendirme:</h4>
            
            <div className="score-level-info">
              <span className={`level-badge ${personalizedScore.score_level.level || 'moderate'}`}>
                {personalizedScore.score_level.description || personalizedScore.score_level.level || 'Orta'}
              </span>
            </div>
            
            {personalizedScore.score_level.breakdown && (
              <div className="breakdown-grid">
                {Object.entries(personalizedScore.score_level.breakdown).map(([key, value]) => (
                  <div key={key} className="breakdown-item">
                    <span className="breakdown-label">{key}:</span>
                    <span className="breakdown-value">
                      {typeof value === 'number' ? 
                        Math.round(value <= 10 ? value * 10 : value) : value}
                      {typeof value === 'number' ? '/100' : ''}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  // Alternatives section
  const AlternativesSection = () => {
    if (!showAlternatives || alternatives.length === 0) {
      return (
        <div className="empty-section">
          <p>🔍 Alternatif ürün bulunamadı</p>
        </div>
      );
    }

    return (
      <div className="alternatives-section">
        <div className="section-header">
          <h3>🔄 Size Daha Uygun Alternatifler ({alternatives.length})</h3>
          <p className="section-description">
            Profilinize daha uygun, benzer ürünler bulundu
          </p>
        </div>
        
        <div className="products-grid">
          {alternatives.map((product, index) => 
            renderProductCard(product, index, true)
          )}
        </div>
      </div>
    );
  };

  // Similar products section
  const SimilarProductsSection = () => {
    if (!showSimilar || recommendations.length === 0) {
      return (
        <div className="empty-section">
          <p>🔍 Öneri bulunamadı</p>
        </div>
      );
    }

    return (
      <div className="similar-products-section">
        <div className="section-header">
          <h3>💡 Size Özel Öneriler ({recommendations.length})</h3>
          <p className="section-description">
            Tercihlerinize göre seçilen ürünler
          </p>
        </div>
        
        <div className="products-grid">
          {recommendations.map((product, index) => 
            renderProductCard(product, index, false)
          )}
        </div>
      </div>
    );
  };

  // Authentication Required Section
  const AuthRequiredSection = () => (
    <div className="auth-required-section">
      <h2>🎯 Kişiselleştirilmiş Öneriler</h2>
      <p>Size özel ürün önerileri görmek için giriş yapmanız gerekmektedir.</p>
      <div className="benefits-list">
        <div className="benefit-item">
          <span className="benefit-icon">🔄</span>
          <span>Profilinize uygun alternatif ürünler</span>
        </div>
        <div className="benefit-item">
          <span className="benefit-icon">📊</span>
          <span>Kişisel uygunluk skorları</span>
        </div>
        <div className="benefit-item">
          <span className="benefit-icon">💡</span>
          <span>Akıllı ML tabanlı öneriler</span>
        </div>
        <div className="benefit-item">
          <span className="benefit-icon">⚖️</span>
          <span>Ürün karşılaştırma</span>
        </div>
      </div>
      <button 
        onClick={() => window.location.href = '/login'} 
        className="login-button"
      >
        🚀 Giriş Yap
      </button>
    </div>
  );

  // Profile waiting section
  const WaitingForProfileSection = () => (
    <div className="waiting-profile-section">
      <h2>🎯 Kişiselleştirilmiş Öneriler</h2>
      <div className="loading-spinner"></div>
      <p>Profil bilgileriniz yükleniyor...</p>
      <small>Bu işlem birkaç saniye sürebilir</small>
    </div>
  );

  // Empty state section
  const EmptyStateSection = () => (
    <div className="empty-recommendations">
      <h3>🔍 Henüz Öneri Bulunamadı</h3>
      <p>Bu ürün için şu anda size özel öneri bulunmamaktadır.</p>
      <button 
        onClick={loadRecommendations} 
        className="reload-button"
        disabled={loading}
      >
        🔄 Yeniden Yükle
      </button>
    </div>
  );

  if (!product) {
    return (
      <div className="personalized-recommendations-container">
        <div className="no-product-error">
          <p>❌ Ürün bilgisi bulunamadı</p>
        </div>
      </div>
    );
  }

  return (
    <div className="personalized-recommendations-container">
      <div className="recommendations-header">
        <h2>🎯 Kişiselleştirilmiş Öneriler</h2>
        <p className="recommendations-subtitle">
          Size özel hazırlanmış ürün önerileri ve alternatifler
        </p>
      </div>

      {!isAuthenticated ? (
        <AuthRequiredSection />
      ) : (
        <>
          {!userProfile ? (
            <WaitingForProfileSection />
          ) : (
            <>
              {loading && <LoadingComponent />}
              
              {error && (
                <ErrorComponent 
                  error={error} 
                  onRetry={loadRecommendations}
                />
              )}
              
              {!loading && !error && (
                <>
                  <PersonalizedScoreSection />
                  
                  <div className="recommendations-tabs">
                    <button 
                      className={`tab-button ${activeTab === 'alternatives' ? 'active' : ''}`}
                      onClick={() => setActiveTab('alternatives')}
                    >
                      🔄 Alternatifler ({alternatives.length})
                    </button>
                    <button 
                      className={`tab-button ${activeTab === 'similar' ? 'active' : ''}`}
                      onClick={() => setActiveTab('similar')}
                    >
                      💡 Öneriler ({recommendations.length})
                    </button>
                  </div>
                  
                  <div className="tab-content">
                    {activeTab === 'alternatives' && <AlternativesSection />}
                    {activeTab === 'similar' && <SimilarProductsSection />}
                  </div>
                  
                  {alternatives.length === 0 && recommendations.length === 0 && (
                    <EmptyStateSection />
                  )}
                  
                  <div className="manual-refresh">
                    <button 
                      onClick={loadRecommendations} 
                      className="manual-refresh-button" 
                      disabled={loading}
                    >
                      {loading ? '🔄 Yükleniyor...' : '🔄 Önerileri Yenile'}
                    </button>
                    <small>Profilinizi güncellediyseniz önerileri yenileyebilirsiniz</small>
                  </div>
                </>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
};

export default PersonalizedRecommendations;