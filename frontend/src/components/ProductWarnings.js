import React, { useState, useEffect, useCallback } from 'react';
import { AlertTriangle, Info, Shield, X, Clock, User, Users } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const ProductWarning = ({ productCode, onClose }) => {
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
    setLoading(true);
    setError(null);
    setWarnings([]);
    setSeverityBreakdown({});
    setWarningStats({ total: 0, byCategory: {}, riskLevel: 'low' });

    try {
      let response;
      
      if (user && authTokens) {
        // Kullanıcı giriş yapmışsa personalized warnings
        response = await fetch(`/api/products/personalized-warnings/?product_code=${productCode}`, {
          method: 'GET', // Changed from POST to GET
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${authTokens.access}`,
          },
        });
      } else {
        // Kullanıcı giriş yapmamışsa general warnings
        response = await fetch(`/api/products/product-warnings-only/?product_code=${productCode}`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          }
        });
      }

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Uyarılar alınamadı');
      }

      const data = await response.json();
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
      
      // Severity breakdown sadece personalized warnings'te gelir
      if (data.severity_breakdown) {
        setSeverityBreakdown(data.severity_breakdown);
      }
      
    } catch (err) {
      console.error('Warning fetch error:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [productCode, user, authTokens, calculateRiskLevel]);

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
      case 'high': return 'text-red-800 bg-red-200';
      case 'medium': return 'text-yellow-800 bg-yellow-200';
      case 'low': return 'text-green-800 bg-green-200';
      default: return 'text-gray-800 bg-gray-200';
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
        return 'border-red-400 bg-red-100';
      case 'warning':
        return 'border-yellow-400 bg-yellow-100';
      case 'info':
        return 'border-blue-400 bg-blue-100';
      default:
        return 'border-gray-400 bg-gray-100';
    }
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-8 max-w-lg w-full mx-4 shadow-2xl">
          <div className="flex flex-col items-center justify-center">
            <svg className="animate-spin h-10 w-10 text-blue-600 mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <p className="text-gray-700 font-medium">Uyarılar yükleniyor...</p>
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

  return (
    <div className="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl p-8 max-w-5xl w-full mx-auto max-h-[90vh] overflow-y-auto shadow-2xl transform transition-all scale-100 ease-out duration-300">
        
        {/* Header Section */}
        <div className="flex justify-between items-start mb-8 border-b pb-6">
          <div className="flex flex-col">
            <h3 className="text-3xl font-bold text-gray-900 mb-2">
              Ürün Uyarıları
            </h3>
            <div className="flex items-center space-x-3 text-sm text-gray-600">
              <span className="inline-flex items-center font-medium">
                {user ? (
                  <>
                    <User className="h-4 w-4 mr-1 text-blue-500" />
                    Kişiselleştirilmiş Uyarılar
                  </>
                ) : (
                  <>
                    <Users className="h-4 w-4 mr-1 text-purple-500" />
                    Genel Uyarılar
                  </>
                )}
              </span>
              <span>•</span>
              <span className="font-semibold">{warningStats.total} Toplam Uyarı</span>
              <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wide ${getRiskLevelColor(warningStats.riskLevel)}`}>
                {warningStats.riskLevel === 'high' ? 'Yüksek Risk' : 
                  warningStats.riskLevel === 'medium' ? 'Orta Risk' : 'Düşük Risk'}
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 transition-colors rounded-full p-1 focus:outline-none focus:ring-2 focus:ring-gray-300"
            aria-label="Kapat"
          >
            <X className="h-7 w-7" />
          </button>
        </div>

        {/* Warning Stats Section */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          {Object.keys(warningStats.byCategory).length > 0 && (
            <div className="bg-gray-50 p-6 rounded-xl shadow-inner border border-gray-100">
              <h4 className="text-base font-bold text-gray-800 mb-4">Uyarı Kategorileri</h4>
              <div className="flex flex-wrap gap-2">
                {Object.entries(warningStats.byCategory).map(([category, count]) => (
                  <span
                    key={category}
                    className="inline-flex items-center px-4 py-2 rounded-full text-sm font-medium bg-blue-100 text-blue-800 border border-blue-200"
                  >
                    {getWarningTypeIcon(category)}
                    <span className="ml-2 capitalize">{category}: <strong className="font-bold">{count}</strong></span>
                  </span>
                ))}
              </div>
            </div>
          )}

          {Object.keys(severityBreakdown).length > 0 && (
            <div className="bg-gray-50 p-6 rounded-xl shadow-inner border border-gray-100">
              <h4 className="text-base font-bold text-gray-800 mb-4">Şiddet Dağılımı</h4>
              <div className="grid grid-cols-3 gap-4 text-sm font-medium">
                <div className="flex flex-col items-center p-3 bg-red-100 rounded-lg">
                  <AlertTriangle className="h-6 w-6 text-red-600 mb-1" />
                  <span className="text-gray-700">Kritik</span>
                  <strong className="text-xl font-bold text-red-800">{severityBreakdown.critical || 0}</strong>
                </div>
                <div className="flex flex-col items-center p-3 bg-yellow-100 rounded-lg">
                  <Shield className="h-6 w-6 text-yellow-600 mb-1" />
                  <span className="text-gray-700">Uyarı</span>
                  <strong className="text-xl font-bold text-yellow-800">{severityBreakdown.warning || 0}</strong>
                </div>
                <div className="flex flex-col items-center p-3 bg-blue-100 rounded-lg">
                  <Info className="h-6 w-6 text-blue-600 mb-1" />
                  <span className="text-gray-700">Bilgi</span>
                  <strong className="text-xl font-bold text-blue-800">{severityBreakdown.info || 0}</strong>
                </div>
              </div>
            </div>
          )}

          {/* This part can be dynamic or static based on your design needs */}
          <div className="bg-gray-50 p-6 rounded-xl shadow-inner border border-gray-100 flex items-center justify-center">
            <div className="text-center">
              <p className="text-sm text-gray-600 mb-2">Bilgiler en güncel haliyle sunulmaktadır.</p>
              <Clock className="h-10 w-10 text-gray-400 mx-auto mb-3" />
              <p className="text-xs text-gray-500 font-mono">Son güncelleme: <br />{new Date().toLocaleString('tr-TR')}</p>
            </div>
          </div>
        </div>

        {/* Warning List Section */}
        {warnings.length === 0 ? (
          <div className="text-center py-12 px-6 bg-green-50 rounded-2xl border-2 border-green-200">
            <Shield className="h-20 w-20 text-green-600 mx-auto mb-6" />
            <h4 className="text-2xl font-bold text-gray-900 mb-3">
              Harika Haber!
            </h4>
            <p className="text-gray-700 text-lg max-w-2xl mx-auto">
              Bu ürün için belirgin bir sağlık veya alerjen uyarısı bulunmamaktadır.
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {warnings.map((warning, index) => {
              const isExpanded = expandedWarnings.has(index);
              const content = warning.message || warning.description || warning.content || 'Detaylı bilgi bulunmamaktadır.';
              const hasLongContent = content.length > 200;
              
              return (
                <div
                  key={index}
                  className={`p-6 rounded-2xl border-l-8 shadow-sm transition-all duration-300 hover:shadow-lg cursor-pointer ${getSeverityColor(warning.severity)}`}
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
                          <div className="flex items-center text-xs font-mono text-gray-500 bg-white bg-opacity-50 rounded-full px-2 py-1 border border-gray-200">
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
                              e.stopPropagation(); // Prevents the outer div's onClick from firing
                              toggleWarningExpansion(index);
                            }}
                            className="mt-2 text-blue-700 hover:text-blue-900 text-sm font-semibold underline transition-colors"
                          >
                            {isExpanded ? 'Daha az göster' : 'Devamını oku'}
                          </button>
                        )}
                      </div>
                      
                      {warning.recommendation && (
                        <div className="mt-4 p-4 bg-white rounded-lg border border-gray-200 shadow-sm">
                          <p className="text-sm text-gray-700 font-semibold mb-1">
                            Öneri:
                          </p>
                          <p className="text-sm text-gray-600">{warning.recommendation}</p>
                        </div>
                      )}
                      
                      {warning.affected_ingredients && warning.affected_ingredients.length > 0 && (
                        <div className="mt-4">
                          <p className="text-xs text-gray-500 font-medium">
                            İlgili bileşenler: <span className="font-semibold">{warning.affected_ingredients.join(', ')}</span>
                          </p>
                        </div>
                      )}
                      
                      {warning.source && (
                        <div className="mt-2">
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
            className="flex items-center px-6 py-3 bg-blue-600 text-white rounded-xl font-bold hover:bg-blue-700 transition-all shadow-md"
          >
            <Clock className="h-5 w-5 mr-2" /> Yenile
          </button>
          <button
            onClick={onClose}
            className="px-8 py-3 bg-gray-200 text-gray-800 rounded-xl font-bold hover:bg-gray-300 transition-all shadow-md"
          >
            Kapat
          </button>
        </div>
      </div>
    </div>
  );
};

export default ProductWarning;