// ProductDetail.js - useAxios hook'u ile optimize edilmiş versiyon

import '../styles/ProductDetail.css';
import React, { useState, useEffect, useCallback, useContext } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import AuthContext from '../context/AuthContext';
import useAxios from '../utils/useAxios';

// Components
import ProductAnalysis from '../components/ProductAnalysis';
import PersonalizedRecommendations from '../components/PersonalizedRecommendations';
import ComprehensiveProductInfo from '../components/ComprehensiveProductInfo';
import ProductWarnings from '../components/ProductWarnings';
import NutritionalRecommendations from '../components/NutritionalRecommendations';

const ProductDetail = () => {
  // Hooks
  const { user, authTokens } = useContext(AuthContext);
  const axiosInstance = useAxios(); // useAxios hook'u kullanılıyor
  const { barcode, productCode } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  
  // State management
  const [product, setProduct] = useState(() => {
    const stateProduct = location.state?.product;
    if (stateProduct) {
      return stateProduct;
    }
    return null;
  });
  
  const [userProfile, setUserProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [productLoading, setProductLoading] = useState(false);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [analysisError, setAnalysisError] = useState(null);
  const [productError, setProductError] = useState(null);
  
  // NutritionalRecommendations için state'ler
  const [nutritionalWarnings, setNutritionalWarnings] = useState([]);
  const [nutritionalRecommendations, setNutritionalRecommendations] = useState([]);

  // Barcode'u resolve et
  const resolvedBarcode = barcode || productCode || location.state?.product?.code || location.state?.product?.product_code;

  // Auth durumunu kontrol et ve profil yükle
  const checkAuthAndLoadProfile = useCallback(async () => {
    try {
      if (!user || !authTokens) {
        console.log('🔐 User not authenticated');
        setLoading(false);
        return;
      }

      console.log('🔐 Loading user profile...');
      const response = await axiosInstance.get('/profile/');
      
      setUserProfile(response.data);
      console.log('✅ Profile loaded successfully');
    } catch (error) {
      console.error('❌ Profile loading error:', error);
      // AuthContext zaten token yenileme işlemini hallediyor
    } finally {
      setLoading(false);
    }
  }, [user, authTokens, axiosInstance]);

  // Ürünü backend'den getir
  const fetchProductFromBackend = useCallback(async (code) => {
    if (!code) {
      setProductError('Ürün kodu bulunamadı');
      setProductLoading(false);
      return;
    }

    setProductLoading(true);
    setProductError(null);
    
    try {
      console.log('📡 Fetching product:', code);
      const response = await axiosInstance.get(`/products/product-detail/${code}/`);
      
      if (response.data) {
        if (response.data.product) {
          setProduct(response.data.product);
          if (response.data.user_analysis) {
            setAnalysisResult(response.data.user_analysis);
          }
        } else if (response.data.product_name || response.data.code) {
          setProduct(response.data);
        } else {
          setProductError('Ürün bulunamadı');
        }
      } else {
        setProductError('Ürün bulunamadı');
      }
    } catch (error) {
      console.error('❌ Product fetch error:', error);
      
      let errorMessage = 'Ürün bilgileri yüklenirken bir hata oluştu';
      if (error.response?.status === 404) {
        errorMessage = 'Ürün bulunamadı';
      } else if (error.response?.status === 500) {
        errorMessage = 'Sunucu hatası. Lütfen daha sonra tekrar deneyin.';
      }
      
      setProductError(errorMessage);
    } finally {
      setProductLoading(false);
    }
  }, [axiosInstance]);

  // Ürün analizi
  const analyzeProduct = useCallback(async () => {
    if (!product || !user) {
      console.log('🧠 Skipping analysis - missing requirements');
      return;
    }

    setAnalysisLoading(true);
    setAnalysisError(null);

    try {
      console.log('🧠 Starting product analysis...');
      
      const productData = {
        code: product.code || product.product_code,
        product_name: product.product_name,
        brand: product.brand,
        ingredients: product.ingredients,
        nutrition_facts: product.nutrition_facts,
        ...product
      };
      
      const requestPayload = { 
        product_data: productData,
        user_profile: userProfile
      };
      
      const response = await axiosInstance.post('/products/analyze/', requestPayload);

      console.log('✅ Analysis response received');
      setAnalysisResult(response.data);
      
    } catch (error) {
      console.error('❌ Analysis error:', error);
      setAnalysisError('Ürün analizi sırasında bir hata oluştu. Lütfen tekrar deneyin.');
    } finally {
      setAnalysisLoading(false);
    }
  }, [product, user, userProfile, axiosInstance]);

  // NutritionalRecommendations callback'leri
  const handleWarningGenerated = useCallback((warning) => {
    setNutritionalWarnings(prev => {
      const exists = prev.some(w => 
        w.title === warning.title && w.message === warning.message
      );
      if (!exists) {
        return [...prev, warning];
      }
      return prev;
    });
  }, []);

  const handleRecommendationGenerated = useCallback((recommendation) => {
    setNutritionalRecommendations(prev => {
      const exists = prev.some(r => 
        r.title === recommendation.title && r.message === recommendation.message
      );
      if (!exists) {
        return [...prev, recommendation];
      }
      return prev;
    });
  }, []);

  // Navigation handlers
  const handleLoginRedirect = () => {
    navigate('/login', {
      state: {
        from: location.pathname,
        returnUrl: `/product/${resolvedBarcode}`,
        productData: product
      }
    });
  };

  const handleBackToSearch = () => {
    navigate('/search');
  };

  // PersonalizedRecommendations için ürün seçim handler'ı
  const handleProductSelect = useCallback((selectedProduct) => {
    console.log('🔄 Product selected from recommendations:', selectedProduct.product_name);
    
    const newBarcode = selectedProduct.product_code || selectedProduct.code || selectedProduct.id;
    
    if (newBarcode) {
      // State'leri temizle
      setProduct(selectedProduct);
      setAnalysisResult(null);
      setAnalysisError(null);
      setProductError(null);
      setNutritionalWarnings([]);
      setNutritionalRecommendations([]);
      
      // URL'i güncelle
      navigate(`/product/${newBarcode}`, {
        state: { product: selectedProduct },
        replace: true
      });
      
      // Sayfayı yukarı kaydır
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }, [navigate]);

  // Retry function
  const handleRetryOperation = useCallback(async (operation) => {
    console.log(`🔄 Retrying operation: ${operation}`);
    
    switch (operation) {
      case 'product':
        if (resolvedBarcode) {
          await fetchProductFromBackend(resolvedBarcode);
        }
        break;
      case 'analysis':
        await analyzeProduct();
        break;
      case 'auth':
        await checkAuthAndLoadProfile();
        break;
      default:
        console.warn('Unknown retry operation:', operation);
    }
  }, [resolvedBarcode, fetchProductFromBackend, analyzeProduct, checkAuthAndLoadProfile]);

  // Effects
  useEffect(() => {
    checkAuthAndLoadProfile();
  }, [checkAuthAndLoadProfile]);

  useEffect(() => {
    if (!product && resolvedBarcode && !productLoading) {
      fetchProductFromBackend(resolvedBarcode);
    }
  }, [product, resolvedBarcode, productLoading, fetchProductFromBackend]);

  useEffect(() => {
    if (user && userProfile && product && !loading && !analysisResult && !analysisLoading) {
      analyzeProduct();
    }
  }, [user, userProfile, product, loading, analysisResult, analysisLoading, analyzeProduct]);

  // Loading states
  if (loading || productLoading) {
    return (
      <div className="product-detail-container">
        <div className="loading-message">
          <h2>Yükleniyor...</h2>
          <p>{productLoading ? 'Ürün bilgileri yükleniyor...' : 'Profil bilgileri yükleniyor...'}</p>
          <div style={{ marginTop: '10px', fontSize: '14px', color: '#666' }}>
            Barkod: {resolvedBarcode || 'Bulunamadı'}
          </div>
        </div>
      </div>
    );
  }

  // Error states
  if (productError || (!product && resolvedBarcode)) {
    return (
      <div className="product-detail-container">
        <div className="error-message">
          <h2>Ürün bulunamadı</h2>
          <p>{productError || 'Ürün bilgileri yüklenemedi. Lütfen arama sayfasından bir ürün seçin.'}</p>
          <div style={{ marginTop: '20px', display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            <button onClick={handleBackToSearch} className="back-button">
              Arama Sayfasına Dön
            </button>
            <button onClick={() => handleRetryOperation('product')} className="retry-button">
              Tekrar Dene
            </button>
          </div>
        </div>
      </div>
    );
  }

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

  // Main render
  return (
    <div className="product-detail-container">
      <div className="product-detail-header">
        <button onClick={handleBackToSearch} className="back-button">
          ← Arama Sayfasına Dön
        </button>
      </div>

      {/* NutritionalRecommendations */}
      {product && (
        <NutritionalRecommendations
          product={product}
          userProfile={userProfile}
          onWarningGenerated={handleWarningGenerated}
          onRecommendationGenerated={handleRecommendationGenerated}
          axiosInstance={axiosInstance} // useAxios instance'ı geçiliyor
        />
      )}

      <div className="product-detail-content">
        {/* Ana Ürün Bilgileri */}
        <ComprehensiveProductInfo 
          product={product} 
          analysisResult={analysisResult}
        />

        {/* Beslenme Uyarıları ve Önerileri */}
        {(nutritionalWarnings.length > 0 || nutritionalRecommendations.length > 0) && (
          <div className="nutritional-insights">
            {nutritionalWarnings.length > 0 && (
              <div className="nutritional-warnings">
                <h3>⚠️ Beslenme Uyarıları</h3>
                {nutritionalWarnings.map((warning, index) => (
                  <div key={index} className={`warning-item ${warning.type} ${warning.severity}`}>
                    <h4>{warning.title}</h4>
                    <p>{warning.message}</p>
                    {warning.details && <small>{warning.details}</small>}
                  </div>
                ))}
              </div>
            )}
            
            {nutritionalRecommendations.length > 0 && (
              <div className="nutritional-recommendations">
                <h3>💡 Beslenme Önerileri</h3>
                {nutritionalRecommendations.map((recommendation, index) => (
                  <div key={index} className={`recommendation-item ${recommendation.type}`}>
                    <h4>{recommendation.title}</h4>
                    <p>{recommendation.message}</p>
                    {recommendation.details && <small>{recommendation.details}</small>}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Ürün Uyarıları */}
        {user && product && (
          <ProductWarnings
            product={product}
            showFullAnalysis={true}
            autoLoad={true}
            axiosInstance={axiosInstance}
          />
        )}

        {/* Kişiselleştirilmiş Ürün Analizi */}
        <ProductAnalysis
          productCode={product?.code || product?.product_code}
          loading={loading}
          isAuthenticated={!!user}
          analysisLoading={analysisLoading}
          analysisError={analysisError}
          analysisResult={analysisResult}
          userProfile={userProfile}
          onLoginRedirect={handleLoginRedirect}
          onAnalyze={analyzeProduct}
          axiosInstance={axiosInstance}
        />

        {/* Analysis Error Handling */}
        {analysisError && user && (
          <div style={{ 
            margin: '20px 0', 
            padding: '15px', 
            backgroundColor: '#fff3cd', 
            border: '1px solid #ffeaa7',
            borderRadius: '8px',
            color: '#856404'
          }}>
            <h4>⚠️ Analiz Hatası</h4>
            <p>{analysisError}</p>
            <button onClick={() => handleRetryOperation('analysis')} className="retry-button">
              Analizi Tekrar Dene
            </button>
          </div>
        )}

        {/* Kişiselleştirilmiş Öneriler */}
        <PersonalizedRecommendations
          product={product}
          isAuthenticated={!!user}
          userProfile={userProfile}
          onProductClick={handleProductSelect}
          showAlternatives={true}
          showSimilar={true}
          autoLoad={true}
          axiosInstance={axiosInstance}
        />

        {/* Debug Information */}
        {process.env.NODE_ENV === 'development' && (
          <div className="debug-info" style={{ 
            marginTop: '40px', 
            padding: '20px', 
            backgroundColor: '#f8f9fa', 
            border: '1px solid #dee2e6',
            borderRadius: '8px',
            fontSize: '12px'
          }}>
            <h4>🔧 Debug Info (Development Only)</h4>
            <div><strong>Product:</strong> {product ? '✅' : '❌'}</div>
            <div><strong>Authenticated:</strong> {user ? '✅' : '❌'}</div>
            <div><strong>Analysis Result:</strong> {analysisResult ? '✅' : '❌'}</div>
            <div><strong>Nutritional Warnings:</strong> {nutritionalWarnings.length}</div>
            <div><strong>Nutritional Recommendations:</strong> {nutritionalRecommendations.length}</div>
            <div><strong>Resolved Barcode:</strong> {resolvedBarcode || 'None'}</div>
            <div><strong>Auth Token:</strong> {authTokens ? 'Present' : 'Missing'}</div>
          </div>
        )}
      </div>
    </div>
  );
}

export default ProductDetail;