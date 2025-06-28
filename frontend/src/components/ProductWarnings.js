import React, { useState, useEffect, useCallback } from 'react';
import { AlertTriangle, Info, Shield, X, Clock, User, Users, LogIn } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const ProductWarning = ({ productCode, onClose, axiosInstance }) => {
  const [warnings, setWarnings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [severityBreakdown, setSeverityBreakdown] = useState({});
  const [warningStats, setWarningStats] = useState({
    total: 0,
    byCategory: {},
    riskLevel: 'low'
  });
  const [expandedWarnings, setExpandedWarnings] = useState(new Set());
  const { user, authTokens } = useAuth();

  const calculateRiskLevel = useCallback((warnings) => {
    const criticalCount = warnings.filter(w => w.severity === 'critical').length;
    const warningCount = warnings.filter(w => w.severity === 'warning').length;
    
    if (criticalCount > 0) return 'high';
    if (warningCount > 2) return 'medium';
    return 'low';
  }, []);

  const fetchWarnings = useCallback(async () => {
    // Kullanıcı giriş yapmamışsa warnings gösterme
    if (!user || !authTokens) {
      setLoading(false);
      setError('Uyarıları görmek için giriş yapmanız gerekiyor.');
      return;
    }

    setLoading(true);
    setError(null);
    setWarnings([]);
    setSeverityBreakdown({});
    setWarningStats({ total: 0, byCategory: {}, riskLevel: 'low' });

    try {
      console.log('📡 Fetching personalized warnings for:', productCode);
      
      let response;
      if (axiosInstance) {
        // axiosInstance kullan (önerilen)
        response = await axiosInstance.get(`/products/personalized-score/?product_code=${productCode}`);
      } else {
        // Fallback: native fetch
        response = await fetch(`/api/products/personalized-score/?product_code=${productCode}`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${authTokens.access}`,
          },
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.error || 'Uyarılar alınamadı');
        }
        response = { data: await response.json() };
      }

      const data = response.data;
      console.log('✅ Personalized warnings received:', data);
      
      // Backend'den gelen data yapısına göre warnings'leri al
      const fetchedWarnings = data.warnings || [];
      
      setWarnings(fetchedWarnings);
      
      // Warning stats hesaplama
      const stats = {
        total: data.warning_count || fetchedWarnings.length,
        byCategory: {},
        riskLevel: calculateRiskLevel(fetchedWarnings)
      };
      
      // Kategori bazında gruplandırma
      fetchedWarnings.forEach(warning => {
        const category = warning.category || warning.type || 'Diğer';
        stats.byCategory[category] = (stats.byCategory[category] || 0) + 1;
      });
      
      setWarningStats(stats);
      
      // Severity breakdown
      if (data.severity_breakdown) {
        setSeverityBreakdown(data.severity_breakdown);
      }
      
    } catch (err) {
      console.error('❌ Warning fetch error:', err);
      setError(err.message || 'Uyarılar yüklenirken bir hata oluştu');
    } finally {
      setLoading(false);
    }
  }, [productCode, user, authTokens, calculateRiskLevel, axiosInstance]);

  useEffect(() => {
    if (productCode) {
      fetchWarnings();
    }
  }, [productCode, fetchWarnings]);

  const toggleWarningExpansion = (index) => {
    const newExpanded = new Set(expandedWarnings);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedWarnings(newExpanded);
  };

  const getRiskLevelColor = (level) => {
    switch (level) {
      case 'high': return 'text-red-800 bg-red-200 border-red-300';
      case 'medium': return 'text-yellow-800 bg-yellow-200 border-yellow-300';
      case 'low': return 'text-green-800 bg-green-200 border-green-300';
      default: return 'text-gray-800 bg-gray-200 border-gray-300';
    }
  };

  const getWarningTypeIcon = (type) => {
    switch (type?.toLowerCase()) {
      case 'allergy':
      case 'allergen':
        return <AlertTriangle className="h-4 w-4 text-red-500" />;
      case 'health':
      case 'medical':
        return <Shield className="h-4 w-4 text-blue-500" />;
      case 'pregnancy':
        return <User className="h-4 w-4 text-purple-500" />;
      case 'children':
      case 'child':
        return <Users className="h-4 w-4 text-orange-500" />;
      default:
        return <Info className="h-4 w-4 text-gray-500" />;
    }
  };

  const getSeverityIcon = (severity) => {
    switch (severity) {
      case 'critical':
        return <AlertTriangle className="h-5 w-5 text-red-600" />;
      case 'warning':
        return <Shield className="h-5 w-5 text-yellow-600" />;
      case 'info':
        return <Info className="h-5 w-5 text-blue-600" />;
      default:
        return <Info className="h-5 w-5 text-gray-600" />;
    }
  };

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'critical':
        return 'border-red-500 bg-red-50 hover:bg-red-100';
      case 'warning':
        return 'border-yellow-500 bg-yellow-50 hover:bg-yellow-100';
      case 'info':
        return 'border-blue-500 bg-blue-50 hover:bg-blue-100';
      default:
        return 'border-gray-500 bg-gray-50 hover:bg-gray-100';
    }
  };

  // Kullanıcı giriş yapmamışsa login önerisi göster
  if (!user || !authTokens) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-8 max-w-lg w-full mx-4 shadow-2xl">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-xl font-bold text-gray-900">Kişiselleştirilmiş Uyarılar</h3>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
              aria-label="Kapat"
            >
              <X className="h-6 w-6" />
            </button>
          </div>
          
          <div className="text-center py-8">
            <LogIn className="h-16 w-16 text-blue-500 mx-auto mb-4" />
            <h4 className="text-lg font-semibold text-gray-900 mb-2">
              Giriş Yapın
            </h4>
            <p className="text-gray-600 mb-6">
              Ürün uyarılarını görmek için profilinizle giriş yapmanız gerekiyor. 
              Bu sayede size özel sağlık ve allerji uyarılarını görebilirsiniz.
            </p>
            <div className="flex gap-3 justify-center">
              <button
                onClick={() => window.location.href = '/login'}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-colors"
              >
                Giriş Yap
              </button>
              <button
                onClick={onClose}
                className="px-6 py-2 bg-gray-200 text-gray-800 rounded-lg font-semibold hover:bg-gray-300 transition-colors"
              >
                Kapat
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-8 max-w-lg w-full mx-4 shadow-2xl">
          <div className="flex flex-col items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mb-4"></div>
            <p className="text-gray-700 font-medium">Kişiselleştirilmiş uyarılar yükleniyor...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 shadow-xl">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-xl font-bold text-gray-900">Hata</h3>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
              aria-label="Kapat"
            >
              <X className="h-6 w-6" />
            </button>
          </div>
          <div className="flex items-center p-5 bg-red-50 border border-red-200 rounded-xl text-red-800">
            <AlertTriangle className="h-6 w-6 mr-3 flex-shrink-0" />
            <div>
              <p className="font-semibold mb-1">Uyarılar alınamadı.</p>
              <p className="text-sm">Hata: {error}</p>
              <button
                onClick={fetchWarnings}
                className="mt-2 text-sm font-semibold text-red-700 underline hover:text-red-900 transition-colors"
              >
                Tekrar dene
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Geri kalan kod aynı kalacak - warnings listesi vs.
  return (
    <div className="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl p-8 max-w-5xl w-full mx-auto max-h-[90vh] overflow-y-auto shadow-2xl transform transition-all scale-100 ease-out duration-300">
        
        {/* Header Section */}
        <div className="flex justify-between items-start mb-8 border-b pb-6">
          <div className="flex flex-col">
            <h3 className="text-3xl font-bold text-gray-900 mb-2">
              Kişiselleştirilmiş Uyarılar
            </h3>
            <div className="flex items-center space-x-3 text-sm text-gray-600">
              <span className="inline-flex items-center font-medium">
                <User className="h-4 w-4 mr-1 text-blue-500" />
                Kişiselleştirilmiş Uyarılar
              </span>
              <span>•</span>
              <span className="font-semibold">{warningStats.total} Toplam Uyarı</span>
              <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wide border ${getRiskLevelColor(warningStats.riskLevel)}`}>
                {warningStats.riskLevel === 'high' ? 'Yüksek Risk' : 
                  warningStats.riskLevel === 'medium' ? 'Orta Risk' : 'Düşük Risk'}
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 transition-colors rounded-full p-2 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-gray-300"
            aria-label="Kapat"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        {/* Warning Stats Section */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          {Object.keys(warningStats.byCategory).length > 0 && (
            <div className="bg-gradient-to-br from-blue-50 to-indigo-100 p-6 rounded-xl shadow-sm border border-blue-200">
              <h4 className="text-base font-bold text-gray-800 mb-4 flex items-center">
                <Info className="h-5 w-5 text-blue-600 mr-2" />
                Uyarı Kategorileri
              </h4>
              <div className="flex flex-wrap gap-2">
                {Object.entries(warningStats.byCategory).map(([category, count]) => (
                  <span
                    key={category}
                    className="inline-flex items-center px-3 py-2 rounded-full text-sm font-medium bg-white text-blue-800 border border-blue-300 shadow-sm"
                  >
                    {getWarningTypeIcon(category)}
                    <span className="ml-2 capitalize">{category}: <strong className="font-bold">{count}</strong></span>
                  </span>
                ))}
              </div>
            </div>
          )}

          {Object.keys(severityBreakdown).length > 0 && (
            <div className="bg-gradient-to-br from-purple-50 to-pink-100 p-6 rounded-xl shadow-sm border border-purple-200">
              <h4 className="text-base font-bold text-gray-800 mb-4 flex items-center">
                <AlertTriangle className="h-5 w-5 text-purple-600 mr-2" />
                Şiddet Dağılımı
              </h4>
              <div className="grid grid-cols-3 gap-3 text-sm font-medium">
                <div className="flex flex-col items-center p-3 bg-white rounded-lg border border-red-200 shadow-sm">
                  <AlertTriangle className="h-6 w-6 text-red-600 mb-1" />
                  <span className="text-gray-700">Kritik</span>
                  <strong className="text-xl font-bold text-red-800">{severityBreakdown.critical || 0}</strong>
                </div>
                <div className="flex flex-col items-center p-3 bg-white rounded-lg border border-yellow-200 shadow-sm">
                  <Shield className="h-6 w-6 text-yellow-600 mb-1" />
                  <span className="text-gray-700">Uyarı</span>
                  <strong className="text-xl font-bold text-yellow-800">{severityBreakdown.warning || 0}</strong>
                </div>
                <div className="flex flex-col items-center p-3 bg-white rounded-lg border border-blue-200 shadow-sm">
                  <Info className="h-6 w-6 text-blue-600 mb-1" />
                  <span className="text-gray-700">Bilgi</span>
                  <strong className="text-xl font-bold text-blue-800">{severityBreakdown.info || 0}</strong>
                </div>
              </div>
            </div>
          )}

          {/* Timestamp Card */}
          <div className="bg-gradient-to-br from-gray-50 to-gray-100 p-6 rounded-xl shadow-sm border border-gray-200 flex items-center justify-center">
            <div className="text-center">
              <p className="text-sm text-gray-600 mb-2">Bilgiler en güncel haliyle sunulmaktadır.</p>
              <Clock className="h-10 w-10 text-gray-400 mx-auto mb-3" />
              <p className="text-xs text-gray-500 font-mono">
                Son güncelleme: <br />
                {new Date().toLocaleString('tr-TR')}
              </p>
            </div>
          </div>
        </div>

        {/* Warning List Section */}
        {warnings.length === 0 ? (
          <div className="text-center py-12 px-6 bg-gradient-to-br from-green-50 to-emerald-100 rounded-2xl border-2 border-green-200">
            <Shield className="h-20 w-20 text-green-600 mx-auto mb-6" />
            <h4 className="text-2xl font-bold text-gray-900 mb-3">
              Harika Haber!
            </h4>
            <p className="text-gray-700 text-lg max-w-2xl mx-auto">
              Profilinize göre bu ürün için herhangi bir sağlık veya alerjen uyarısı bulunmamaktadır.
            </p>
            <div className="mt-6 inline-flex items-center px-4 py-2 bg-green-200 text-green-800 rounded-full text-sm font-medium">
              <Shield className="h-4 w-4 mr-2" />
              Sizin İçin Güvenli
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {warnings.map((warning, index) => {
              const isExpanded = expandedWarnings.has(index);
              const content = warning.message || warning.description || warning.content || 'Detaylı bilgi bulunmamaktadır.';
              const hasLongContent = content.length > 200;
              
              return (
                <div
                  key={index}
                  className={`p-6 rounded-xl border-l-4 shadow-sm transition-all duration-300 hover:shadow-md ${hasLongContent ? 'cursor-pointer' : ''} ${getSeverityColor(warning.severity)}`}
                  onClick={() => hasLongContent && toggleWarningExpansion(index)}
                >
                  <div className="flex items-start">
                    <div className="flex-shrink-0 mr-4 mt-1">
                      {getSeverityIcon(warning.severity)}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-2">
                        <h5 className="font-bold text-lg text-gray-900">
                          {warning.title || warning.type || 'Uyarı'}
                        </h5>
                        {warning.timestamp && (
                          <div className="flex items-center text-xs font-mono text-gray-500 bg-white bg-opacity-70 rounded-full px-3 py-1 border border-gray-300">
                            <Clock className="h-3 w-3 mr-1" />
                            {new Date(warning.timestamp).toLocaleDateString('tr-TR')}
                          </div>
                        )}
                      </div>
                      
                      <div className="text-gray-800 text-base leading-relaxed">
                        <p className={`${hasLongContent && !isExpanded ? 'line-clamp-3' : ''}`}>
                          {content}
                        </p>
                        {hasLongContent && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              toggleWarningExpansion(index);
                            }}
                            className="mt-2 text-blue-700 hover:text-blue-900 text-sm font-semibold underline transition-colors"
                          >
                            {isExpanded ? 'Daha az göster' : 'Devamını oku'}
                          </button>
                        )}
                      </div>
                      
                      {warning.recommendation && (
                        <div className="mt-4 p-4 bg-white rounded-lg border border-gray-300 shadow-sm">
                          <p className="text-sm text-gray-700 font-semibold mb-1 flex items-center">
                            <Info className="h-4 w-4 mr-1 text-blue-500" />
                            Öneri:
                          </p>
                          <p className="text-sm text-gray-600">{warning.recommendation}</p>
                        </div>
                      )}
                      
                      {warning.affected_ingredients && warning.affected_ingredients.length > 0 && (
                        <div className="mt-4 p-3 bg-yellow-50 rounded-lg border border-yellow-200">
                          <p className="text-xs text-gray-600 font-medium mb-1">
                            İlgili bileşenler:
                          </p>
                          <div className="flex flex-wrap gap-1">
                            {warning.affected_ingredients.map((ingredient, idx) => (
                              <span key={idx} className="inline-block px-2 py-1 bg-yellow-200 text-yellow-800 text-xs rounded-full font-medium">
                                {ingredient}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      {warning.source && (
                        <div className="mt-3 pt-3 border-t border-gray-200">
                          <p className="text-xs text-gray-400 font-mono">
                            Kaynak: {warning.source}
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Footer Buttons */}
        <div className="flex justify-end items-center mt-10 pt-6 border-t border-gray-200 space-x-4">
          <button
            onClick={fetchWarnings}
            className="flex items-center px-6 py-3 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-700 transition-all shadow-md hover:shadow-lg"
          >
            <Clock className="h-4 w-4 mr-2" />
            Yenile
          </button>
          <button
            onClick={onClose}
            className="px-8 py-3 bg-gray-200 text-gray-800 rounded-xl font-semibold hover:bg-gray-300 transition-all shadow-md hover:shadow-lg"
          >
            Kapat
          </button>
        </div>
      </div>
    </div>
  );
};

export default ProductWarning;