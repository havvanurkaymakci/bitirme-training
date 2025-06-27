import React from 'react';



// Uyarı Component'i - Backend'den gelen farklı uyarı tiplerini birleştirecek şekilde güncellendi.
const WarningsSection = ({ warnings, onRefreshWarnings, loading }) => {
  const getSeverityIcon = (severity) => {
    switch (severity) {
      case 'critical':
        return '🚨';
      case 'high':
        return '⚠️';
      case 'medium':
        return '⚡';
      case 'low':
        return 'ℹ️';
      default:
        return '⚠️';
    }
  };

  const getSeverityText = (severity) => {
    switch (severity) {
      case 'critical':
        return 'Kritik';
      case 'high':
        return 'Yüksek';
      case 'medium':
        return 'Orta';
      case 'low':
        return 'Düşük';
      default:
        return 'Bilinmiyor';
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
        <div key={index} className={`warning-card severity-${warning.severity || 'medium'}`}>
          <div className="warning-header">
            <h3>
              {getSeverityIcon(warning.severity)} {warning.title || warning.message || warning}
            </h3>
            <span className={`severity-badge ${warning.severity || 'medium'}`}>
              {getSeverityText(warning.severity)}
            </span>
          </div>
          {warning.message && warning.title && (
            <p className="warning-message">{warning.message}</p>
          )}
          {warning.details && (
            <p className="warning-details">{warning.details}</p>
          )}
          {warning.affected_conditions && warning.affected_conditions.length > 0 && (
            <div className="affected-conditions">
              <strong>🎯 İlgili durumlar:</strong> {warning.affected_conditions.join(', ')}
            </div>
          )}
          {warning.recommendation && (
            <div className="warning-recommendation">
              <strong>💡 Öneri:</strong> {warning.recommendation}
            </div>
          )}
        </div>
      ))}
    </div>
  );
};

// Ana Analysis Component'i - Backend'in yeni API yapısına göre güncellendi.
const ProductAnalysis = ({
  productCode,
  loading,
  isAuthenticated,
  analysisLoading,
  analysisError,
  analysisResult,
  userProfile,
  onLoginRedirect,
  onAnalyze,
  onRefreshWarnings,
  renderUserProfileInfo
}) => {
  // Giriş yapmamış kullanıcı için render
  if (!isAuthenticated) {
    return (
      <div className="product-analysis-section">
        <div className="analysis-card">
          <div className="analysis-header">
            <h2>🔍 Kişiselleştirilmiş Analiz</h2>
          </div>
          <div className="login-required">
            <div className="login-message">
              <h3>🔒 Giriş Yapın</h3>
              <p>
                Bu ürünün sizin için uygun olup olmadığını öğrenmek, kişisel sağlık uyarılarını
                görüntülemek ve özelleştirilmiş öneriler almak için giriş yapmanız gerekiyor.
              </p>
              <button onClick={onLoginRedirect} className="login-button">
                Giriş Yap / Kayıt Ol
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Yükleme durumu
  if (loading) {
    return (
      <div className="product-analysis-section">
        <div className="analysis-card">
          <div className="loading-state">
            <div className="spinner"></div>
            <p>Profil bilgileriniz yükleniyor...</p>
          </div>
        </div>
      </div>
    );
  }

  // Helper function to get all warnings from the backend response
  const getAllWarnings = (result) => {
    if (!result) return [];
    const allWarnings = [];

    // Backend's old structure
    if (result.warnings) {
      allWarnings.push(...result.warnings);
    }

    // Backend's new detailed analysis structure
    if (result.health_alerts) {
      allWarnings.push(...result.health_alerts);
    }
    if (result.allergen_alerts) {
      allWarnings.push(...result.allergen_alerts);
    }
    if (result.medical_alerts) {
      allWarnings.push(...result.medical_alerts);
    }
    if (result.dietary_warnings) {
      allWarnings.push(...result.dietary_warnings);
    }
    if (result.general_warnings) {
      allWarnings.push(...result.general_warnings);
    }
    
    // ML analysis warnings (if any)
    if (result.ml_analysis?.warnings) {
      allWarnings.push(...result.ml_analysis.warnings);
    }

    // Filter out duplicates if needed, but for now, just combine
    return allWarnings;
  };

  // Helper functions for scoring
  const getScoreClass = (score) => {
    if (score >= 80) return 'excellent';
    if (score >= 60) return 'good';
    if (score >= 40) return 'fair';
    return 'poor';
  };

  const getScoreText = (score) => {
    if (score >= 80) return 'Mükemmel';
    if (score >= 60) return 'İyi';
    if (score >= 40) return 'Orta';
    return 'Zayıf';
  };

  const getMLScoreClass = (score) => {
    if (score >= 8) return 'excellent';
    if (score >= 6) return 'good';
    if (score >= 4) return 'fair';
    return 'poor';
  };

  const getMLScoreText = (score) => {
    if (score >= 8) return 'Mükemmel';
    if (score >= 6) return 'İyi';
    if (score >= 4) return 'Orta';
    return 'Zayıf';
  };

  const formatScoreLabel = (key) => {
    const labels = {
      'health_score': 'Sağlık Skoru',
      'nutrition_score': 'Beslenme Skoru',
      'ingredient_score': 'İçerik Skoru',
      'allergen_score': 'Alerjen Skoru',
      'personal_compatibility': 'Kişisel Uyumluluk'
    };
    return labels[key] || key;
  };

  const formatAnalysisLabel = (key) => {
    const labels = {
      'health_impact': 'Sağlık Etkisi',
      'nutrition_quality': 'Beslenme Kalitesi',
      'ingredient_risk': 'İçerik Riski',
      'allergen_risk': 'Alerjen Riski',
      'personal_fit': 'Kişisel Uygunluk'
    };
    return labels[key] || key;
  };

  const getCompatibilityIcon = (status) => {
    switch (status) {
      case 'compatible':
        return '✅';
      case 'partially_compatible':
        return '⚠️';
      case 'incompatible':
        return '❌';
      default:
        return '❓';
    }
  };

  const getCompatibilityText = (status) => {
    switch (status) {
      case 'compatible':
        return 'Uyumlu';
      case 'partially_compatible':
        return 'Kısmen Uyumlu';
      case 'incompatible':
        return 'Uyumsuz';
      default:
        return 'Bilinmiyor';
    }
  };

  // Ana analiz bölümü
  return (
    <div className="product-analysis-section">
      <div className="analysis-card">
        <div className="analysis-header">
          <h2>🔍 Kişiselleştirilmiş Analiz</h2>
          <div className="analysis-actions">
            <button
              onClick={onAnalyze}
              className="analyze-button"
              disabled={analysisLoading}
            >
              {analysisLoading ? '🔄 Analiz Ediliyor...' : '🎯 Yeniden Analiz Et'}
            </button>
          </div>
        </div>

        {/* Kullanıcı Profil Bilgileri */}
        {renderUserProfileInfo && renderUserProfileInfo()}

        {/* Analiz Hatası */}
        {analysisError && (
          <div className="analysis-error">
            <h3>❌ Analiz Hatası</h3>
            <p>{analysisError}</p>
            <button onClick={onAnalyze} className="retry-button">
              🔄 Tekrar Dene
            </button>
          </div>
        )}

        {/* Analiz Yükleniyor */}
        {analysisLoading && (
          <div className="analysis-loading">
            <div className="spinner"></div>
            <p>Ürün profilinize göre analiz ediliyor...</p>
          </div>
        )}

        {/* Analiz Sonuçları */}
        {analysisResult && !analysisLoading && (
          <div className="analysis-results">
            {/* ML Analysis Score - Backend'deki yapıya uygun */}
            {analysisResult.ml_analysis && (
              <div className="ml-analysis-section">
                <h3>🤖 AI Destekli Analiz</h3>
                <div
                  className={`score-display score-${getMLScoreClass(
                    analysisResult.ml_analysis.personalized_score
                  )}`}
                >
                  <div className="score-number">
                    {analysisResult.ml_analysis.personalized_score.toFixed(1)}/10
                  </div>
                  <div className="score-text">
                    {getMLScoreText(analysisResult.ml_analysis.personalized_score)}
                  </div>
                </div>
                {analysisResult.ml_analysis.score_level && (
                  <div className="score-breakdown">
                    {Object.entries(analysisResult.ml_analysis.score_level).map(([key, value]) => (
                      <div key={key} className="score-item">
                        <span className="score-label">{formatScoreLabel(key)}:</span>
                        <span className="score-value">
                          {typeof value === 'number' ? value.toFixed(1) : value}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
                {analysisResult.ml_analysis.analysis && (
                  <div className="ml-analysis-details">
                    <h4>🔍 Detaylı Analiz</h4>
                    {Object.entries(analysisResult.ml_analysis.analysis).map(([key, value]) => (
                      <div key={key} className="analysis-detail">
                        <strong>{formatAnalysisLabel(key)}:</strong> {value}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Overall Suitability Score (Rule-based analysis) - Using a dedicated field from the backend */}
            {analysisResult.is_suitable !== undefined && (
              <div className="overall-suitability-section">
                <h3>✅ Uygunluk Değerlendirmesi</h3>
                <div className={`suitability-badge ${analysisResult.is_suitable ? 'suitable' : 'unsuitable'}`}>
                  {analysisResult.is_suitable ? '✅ Sizin İçin Uygun' : '❌ Sizin İçin Uygun Değil'}
                </div>
                {analysisResult.summary && (
                  <p className="suitability-summary">{analysisResult.summary}</p>
                )}
              </div>
            )}

            {/* Uyarılar Section - Backend'den gelen tüm uyarıları göster */}
            <WarningsSection
              warnings={getAllWarnings(analysisResult)}
              onRefreshWarnings={onRefreshWarnings}
              loading={analysisLoading}
            />

            {/* Beslenme Analizi */}
            {analysisResult.nutritional_analysis && Object.keys(analysisResult.nutritional_analysis).length > 0 && (
              <div className="nutrition-analysis-section">
                <h3>🥗 Beslenme Analizi</h3>
                <div className="nutrition-insights">
                  {analysisResult.nutritional_analysis.positive_aspects &&
                    analysisResult.nutritional_analysis.positive_aspects.length > 0 && (
                      <div className="positive-aspects">
                        <h4>✅ Olumlu Yönler</h4>
                        <ul>
                          {analysisResult.nutritional_analysis.positive_aspects.map((aspect, index) => (
                            <li key={index}>{aspect}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                  {analysisResult.nutritional_analysis.concerns &&
                    analysisResult.nutritional_analysis.concerns.length > 0 && (
                      <div className="nutrition-concerns">
                        <h4>⚠️ Dikkat Edilmesi Gerekenler</h4>
                        <ul>
                          {analysisResult.nutritional_analysis.concerns.map((concern, index) => (
                            <li key={index}>{concern}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                  {analysisResult.nutritional_analysis.recommendations &&
                    analysisResult.nutritional_analysis.recommendations.length > 0 && (
                      <div className="nutrition-recommendations">
                        <h4>💡 Öneriler</h4>
                        <ul>
                          {analysisResult.nutritional_analysis.recommendations.map((rec, index) => (
                            <li key={index}>{rec}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                </div>
              </div>
            )}

            {/* Diyet Uyumluluğu */}
            {analysisResult.dietary_compliance && Object.keys(analysisResult.dietary_compliance).length > 0 && (
              <div className="dietary-compliance-section">
                <h3>🍽️ Diyet Uyumluluğu</h3>
                <div className="compliance-list">
                  {Object.entries(analysisResult.dietary_compliance).map(([diet, status]) => (
                    <div key={diet} className={`compliance-item status-${status}`}>
                      <span className="compliance-icon">
                        {status === 'compliant' ? '✅' : status === 'non_compliant' ? '❌' : '❓'}
                      </span>
                      <span className="diet-name">{diet}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Kişiselleştirilmiş Öneriler */}
            {analysisResult.recommendations && analysisResult.recommendations.length > 0 && (
              <div className="personalized-recommendations-section">
                <h3>💫 Kişiselleştirilmiş Öneriler</h3>
                <div className="recommendations-list">
                  {analysisResult.recommendations.map((recommendation, index) => (
                    <div key={index} className="recommendation-item">
                      <h4>{recommendation.title}</h4>
                      <p>{recommendation.description}</p>
                      {recommendation.action && (
                        <div className="recommendation-action">
                          <strong>Önerilen Aksiyon:</strong> {recommendation.action}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* User Profile Usage Info - Backend'den gelen bilgi */}
            {analysisResult.user_profile_used && (
              <div className="profile-usage-info">
                <h3>👤 Kullanılan Profil Bilgileri</h3>
                <div className="profile-usage-details">
                  <div className={`usage-item ${analysisResult.user_profile_used.has_conditions ? 'has-data' : 'no-data'}`}>
                    <span className="usage-icon">{analysisResult.user_profile_used.has_conditions ? '✅' : '❌'}</span>
                    <span>Sağlık Durumları</span>
                  </div>
                  <div className={`usage-item ${analysisResult.user_profile_used.has_allergies ? 'has-data' : 'no-data'}`}>
                    <span className="usage-icon">{analysisResult.user_profile_used.has_allergies ? '✅' : '❌'}</span>
                    <span>Alerjiler</span>
                  </div>
                  <div className={`usage-item ${analysisResult.user_profile_used.has_goals ? 'has-data' : 'no-data'}`}>
                    <span className="usage-icon">{analysisResult.user_profile_used.has_goals ? '✅' : '❌'}</span>
                    <span>Sağlık Hedefleri</span>
                  </div>
                </div>
              </div>
            )}

            {/* Analysis Type Info - Backend'den gelen tip bilgisi */}
            <div className="analysis-info">
              <small>
                📊 Analiz Türü: {
                  analysisResult.analysis_type === 'ml_based'
                    ? 'AI Destekli Analiz'
                    : analysisResult.analysis_type === 'hybrid'
                    ? 'Hibrit Analiz (AI + Kural)'
                    : 'Kural Tabanlı Analiz'
                }
                {analysisResult.product && (
                  <span> | 🏷️ Ürün: {analysisResult.product.product_name || 'Bilinmeyen'}</span>
                )}
                {analysisResult.confidence_score && (
                   <span> | ✨ Güven Seviyesi: %{analysisResult.confidence_score}</span>
                )}
              </small>
            </div>
          </div>
        )}

        {/* Hiç analiz yapılmamış durumu */}
        {!analysisResult && !analysisLoading && !analysisError && (
          <div className="no-analysis">
            <div className="empty-state">
              <h3>🎯 Analiz Bekleniyor</h3>
              <p>Bu ürünün profilinize uygunluğunu değerlendirmek için analiz başlatın.</p>
              <button onClick={onAnalyze} className="start-analysis-button">
                🚀 Analizi Başlat
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ProductAnalysis;