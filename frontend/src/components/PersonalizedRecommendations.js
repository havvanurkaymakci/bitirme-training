import React, { useState, useEffect } from 'react';
import axios from 'axios';
import '../styles/PersonalizedRecommendations.css';

const PersonalizedRecommendations = ({ 
  product, 
  isAuthenticated,
  userProfile,
  onProductClick,
  showAlternatives = true,
  showSimilar = true,
  autoLoad = true
}) => {
  // ✅ DEBUG: Props kontrolü
  console.log('🔍 PersonalizedRecommendations Props:', {
    product: product ? 'Product exists' : 'Product is null/undefined',
    productName: product?.product_name || 'No name',
    isAuthenticated,
    userProfile: userProfile ? 'Profile exists' : 'No profile',
    showAlternatives,
    showSimilar,
    autoLoad
  });

  const [recommendations, setRecommendations] = useState([]);
  const [alternatives, setAlternatives] = useState([]);
  const [personalizedScore, setPersonalizedScore] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('alternatives');

  // ✅ In-memory auth token storage
  const [authToken, setAuthToken] = useState(null);

  useEffect(() => {
    // Token'ı localStorage'dan al (sadece bir kere)
    try {
      const token = localStorage.getItem('authTokens');
      if (token) {
        const tokens = JSON.parse(token);
        setAuthToken(tokens.access);
      }
    } catch (error) {
      console.error('Token parse error:', error);
    }
  }, []);

  useEffect(() => {
    if (isAuthenticated && product && userProfile && autoLoad && authToken) {
      loadRecommendations();
    }
  }, [isAuthenticated, product, userProfile, autoLoad, authToken]);

  // Backend URL'leri için helper function
  const getApiUrl = (endpoint) => {
    const baseUrl = 'http://localhost:8000/api/products';
    return `${baseUrl}/${endpoint}`;
  };

  // ✅ Token helper function - in-memory storage kullanımı
  const getAuthHeaders = () => {
    if (!authToken) return null;
    
    return {
      'Authorization': `Bearer ${authToken}`,
      'Content-Type': 'application/json'
    };
  };

  // ✅ DÜZELTME: Ana önerileri yükle - Backend endpoint'leriyle uyumlu
  const loadRecommendations = async () => {
    if (!product || !isAuthenticated || !userProfile || !authToken) return;

    setLoading(true);
    setError(null);

    try {
      const headers = getAuthHeaders();
      if (!headers) {
        throw new Error('Authentication failed');
      }

      const productCode = product.product_code || product.code || product.id;
      if (!productCode) {
        console.warn('Product code not found, fetching general recommendations.');
      }
      
      const promises = [];

      // 1. ✅ ML tabanlı alternatifler (ürüne özel) - GET request
      if (showAlternatives && productCode) {
        promises.push(
          axios.get(
            getApiUrl('ml-recommendations/'),
            { 
              headers,
              params: {
                product_code: productCode,
                limit: 5,
                min_score: 6.0
              }
            }
          ).then(response => ({type: 'alternatives', data: response.data}))
        );
      }

      // 2. ✅ ML tabanlı genel öneriler - GET request
      if (showSimilar) {
        promises.push(
          axios.get(
            getApiUrl('ml-recommendations/'),
            { 
              headers,
              params: {
                limit: 6,
                categories: product.main_category || product.categories || '',
                min_score: 6.0
              }
            }
          ).then(response => ({type: 'recommendations', data: response.data}))
        );
      }
      
      // 3. ✅ Kişiselleştirilmiş skor - GET request (backend'deki endpoint'e göre)
      if (productCode) {
        promises.push(
          axios.get(
            getApiUrl('personalized-score/'),
            { 
              headers,
              params: {
                product_code: productCode
              }
            }
          ).then(response => ({type: 'score', data: response.data}))
        );
      }

      const results = await Promise.allSettled(promises);

      results.forEach((result, index) => {
        if (result.status === 'fulfilled') {
          const { type, data } = result.value;
          
          switch(type) {
            case 'alternatives':
              // Backend'den gelen response yapısına göre düzeltme
              if (data.type === 'alternatives' && data.alternatives) {
                setAlternatives(data.alternatives);
                console.log('✅ Alternatives loaded:', data.alternatives.length);
              } else if (data.recommendations) {
                // Eğer genel öneri dönerse alternatif olarak kullan
                setAlternatives(data.recommendations);
                console.log('✅ Alternatives (from recommendations) loaded:', data.recommendations.length);
              }
              break;
              
            case 'recommendations':
              // Backend'den gelen response yapısına göre düzeltme
              if (data.type === 'personalized' && data.recommendations) {
                setRecommendations(data.recommendations);
                console.log('✅ Recommendations loaded:', data.recommendations.length);
              } else if (data.alternatives) {
                // Eğer alternatif dönerse öneri olarak kullan
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
          console.error(`❌ ${errorTypes[index]} yükleme hatası:`, result.reason?.response?.data || result.reason?.message);
        }
      });
      
    } catch (error) {
      console.error('❌ Öneriler yükleme hatası:', error);
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

  // ✅ Ürün karşılaştırması yap - POST request (backend endpoint'ine uygun)
  const compareProducts = async (productCodes) => {
    if (!isAuthenticated || productCodes.length < 2 || !authToken) return;

    try {
      const headers = getAuthHeaders();
      if (!headers) return null;

      const response = await axios.post(
        getApiUrl('compare/'),
        { product_codes: productCodes },
        { headers }
      );

      console.log('✅ Karşılaştırma sonucu:', response.data);
      return response.data;
    } catch (error) {
      console.error('❌ Karşılaştırma hatası:', error);
      return null;
    }
  };

  // Sağlık uygunluk skoru rengini belirle
  const getHealthScoreColor = (score) => {
    const normalizedScore = score <= 10 ? score * 10 : score;
    
    if (normalizedScore >= 80) return 'excellent';
    if (normalizedScore >= 60) return 'good';
    if (normalizedScore >= 40) return 'moderate';
    if (normalizedScore >= 20) return 'poor';
    return 'very-poor';
  };

  // ✅ Ürün kartı render - Backend'den gelen veri yapısına uygun
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
              alt={product.product_name}
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
          <h4 className="product-name">{product.product_name}</h4>
          <p className="product-brand">{product.brands || product.brand}</p>
          
          {/* ✅ Backend'den gelen score alanlarına göre düzeltme */}
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
          
          {/* ✅ Backend'den gelen reason alanlarına göre düzeltme */}
          {(product.reason || product.recommendation_reason || product.match_reasons) && (
            <div className="match-reasons">
              <small>
                💡 {product.reason || product.recommendation_reason || 
                     (Array.isArray(product.match_reasons) ? 
                      product.match_reasons.slice(0, 2).join(', ') : product.match_reasons)}
                {product.match_reasons && Array.isArray(product.match_reasons) && product.match_reasons.length > 2 && '...'}
              </small>
            </div>
          )}
          
          {/* ✅ İyileştirme alanları (alternatifler için) */}
          {isAlternative && (product.improvement_areas || product.score_improvement) && (
            <div className="improvement-areas">
              <small>
                ✨ İyileştirme: {product.improvement_areas || 
                  (product.score_improvement ? `+${Math.round(product.score_improvement * 10)} puan` : '')}
              </small>
            </div>
          )}
          
          {/* ✅ Sağlık faydaları (öneriler için) */}
          {!isAlternative && product.health_benefits && Array.isArray(product.health_benefits) && (
            <div className="health-benefits">
              <small>
                🌱 Faydalar: {product.health_benefits.slice(0, 2).join(', ')}
                {product.health_benefits.length > 2 && '...'}
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

  // Yükleme Component'i
  const LoadingComponent = () => (
    <div className="recommendations-loading">
      <div className="loading-spinner"></div>
      <p>🎯 Sizin için özel öneriler hazırlanıyor...</p>
      <small>Bu işlem birkaç saniye sürebilir</small>
    </div>
  );

  // Hata Component'i
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

  // ✅ Kişiselleştirilmiş skor Section - Backend response yapısına uygun
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
            
            {/* ✅ Backend'den gelen analysis yapısına göre düzeltme */}
            {(personalizedScore.analysis?.health_match_reasons || 
              personalizedScore.health_match_reasons || 
              personalizedScore.match_reasons) && (
              <div className="match-reasons-detailed">
                <h4>🎯 Uygunluk Nedenleri:</h4>
                <ul>
                  {(personalizedScore.analysis?.health_match_reasons || 
                    personalizedScore.health_match_reasons || 
                    personalizedScore.match_reasons || []).map((reason, index) => (
                    <li key={index}>{reason}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
        
        {/* ✅ Score breakdown section */}
        {(personalizedScore.score_level || personalizedScore.breakdown) && (
          <div className="score-breakdown">
            <h4>📈 Detaylı Değerlendirme:</h4>
            
            {personalizedScore.score_level && (
              <div className="score-level-info">
                <span className={`level-badge ${personalizedScore.score_level.level}`}>
                  {personalizedScore.score_level.description || personalizedScore.score_level.level}
                </span>
              </div>
            )}
            
            {(personalizedScore.score_level?.breakdown || personalizedScore.breakdown) && (
              <div className="breakdown-grid">
                {Object.entries(personalizedScore.score_level?.breakdown || personalizedScore.breakdown).map(([key, value]) => (
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

  // Alternatif ürünler section
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

  // Benzer ürünler section
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

  // Profil Bekleme Section
  const WaitingForProfileSection = () => (
    <div className="waiting-profile-section">
      <h2>🎯 Kişiselleştirilmiş Öneriler</h2>
      <div className="loading-spinner"></div>
      <p>Profil bilgileriniz yükleniyor...</p>
      <small>Bu işlem birkaç saniye sürebilir</small>
    </div>
  );

  // Boş durum Section
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