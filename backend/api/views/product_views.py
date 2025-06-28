# api/views/product_views.py

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.http import JsonResponse
from django.core.cache import cache
import requests
import logging
import hashlib
import json
from typing import Dict, List, Optional
from datetime import datetime

# Models
from api.models.user_profile import Profile
from api.models.product_features import ProductFeatures

# AI Models - ML tabanlı servisler doğrudan kullanılıyor
from aimodels.ml_models.recommendation_service import ml_recommendation_service
from aimodels.ml_models.ml_product_score_service import ml_product_score_service
from aimodels.product_analysis import ProductAnalyzer  # Sadece kural tabanlı uyarılar için

# Serializers
from api.serializers.product_serializer import (
    ProductFeaturesBaseSerializer, 
    ProductRecommendationSerializer,
    ProductSearchSerializer,
    HealthAnalysisSerializer,
    ProductAlternativesSerializer,
    ProductAlternativesResponseSerializer,
    PersonalizedProductScoreSerializer,
    PersonalizedProductScoreResponseSerializer,
    ProductComparisonSerializer,
    ProductComparisonResponseSerializer,
    HealthAnalysisSerializer,
    MLUserProfileInputSerializer
)

logger = logging.getLogger(__name__)

# OpenFoodFacts API Configuration
OPENFOODFACTS_API_BASE = "https://world.openfoodfacts.org"
OPENFOODFACTS_SEARCH_URL = f"{OPENFOODFACTS_API_BASE}/cgi/search.pl"
OPENFOODFACTS_PRODUCT_URL = f"{OPENFOODFACTS_API_BASE}/api/v0/product"


class OpenFoodFactsProductSerializer:
    """OpenFoodFacts API response serializer"""
    
    @classmethod
    def serialize(cls, raw_product: Dict) -> Optional[Dict]:
        """Clean and format raw product data"""
        try:
            if not raw_product:
                return None
                
            return {
                'code': raw_product.get('_id', raw_product.get('code', '')),
                'product_name': raw_product.get('product_name', ''),
                'brands': raw_product.get('brands', ''),
                'categories': raw_product.get('categories', ''),
                'nutriscore_grade': raw_product.get('nutriscore_grade', '').upper(),
                'nova_group': raw_product.get('nova_group', 0),
                'image_url': raw_product.get('image_url', ''),
                'image_front_url': raw_product.get('image_front_url', ''),
                'image_front_small_url': raw_product.get('image_front_small_url', ''),
                'nutriments': raw_product.get('nutriments', {}),
                'ingredients_text': raw_product.get('ingredients_text', ''),
                'allergens': raw_product.get('allergens', ''),
                'allergens_tags': raw_product.get('allergens_tags', []),
                'additives_tags': raw_product.get('additives_tags', []),
                'labels_tags': raw_product.get('labels_tags', []),
                'completeness': raw_product.get('completeness', 0),
                'last_modified_t': raw_product.get('last_modified_t', 0),
            }
        except Exception as e:
            logger.error(f"Product data serialization error: {str(e)}")
            return None


class OpenFoodFactsResponse:
    """OpenFoodFacts API response wrapper"""
    def __init__(self, success: bool, data: dict = None, error_message: str = None):
        self.success = success
        self.data = data or {}
        self.error_message = error_message


# Helper Functions
def get_user_profile_data(user) -> Dict:
    """Get user profile data for ML analysis"""
    try:
        profile = Profile.objects.get(user=user)
        return MLUserProfileInputSerializer.from_profile(profile)
    except Profile.DoesNotExist:
        return {
            'age': 25,
            'gender': 'Other',
            'height': 170.0,
            'weight': 70.0,
            'bmi': 24.2,
            'activity_level': 'moderate',
            'medical_conditions': [],
            'allergies': [],
            'dietary_preferences': [],
            'health_goals': [],
        }
    except Exception as e:
        logger.error(f"Error getting user profile: {str(e)}")
        return {
            'age': 25,
            'gender': 'Other',
            'height': 170.0,
            'weight': 70.0,
            'bmi': 24.2,
            'activity_level': 'moderate',
            'medical_conditions': [],
            'allergies': [],
            'dietary_preferences': [],
            'health_goals': [],
        }


def generate_cache_key(operation: str, user_id: int, params: dict) -> str:
    """Generate cache key for operations"""
    params_str = json.dumps(params, sort_keys=True)
    key_data = f"{operation}_{user_id}_{params_str}"
    return hashlib.md5(key_data.encode()).hexdigest()


def search_products_api(query: str = "", filters: dict = None, page: int = 1, 
                       page_size: int = 20, fields: list = None) -> OpenFoodFactsResponse:
    """Search products using OpenFoodFacts API"""
    try:
        params = {
            'action': 'process',
            'json': 1,
            'page': page,
            'page_size': page_size,
            'fields': ','.join(fields) if fields else 'code,_id,product_name,brands,categories,nutriscore_grade,nova_group,image_url,nutriments,image_front_url,image_front_small_url,ingredients_text,allergens,allergens_tags,additives_tags,labels_tags,completeness,last_modified_t'
        }
        
        if query:
            params['search_terms'] = query
            
        # Apply filters
        if filters:
            for key, value in filters.items():
                if value:
                    params[key] = ','.join(map(str, value)) if isinstance(value, list) else value
        
        response = requests.get(OPENFOODFACTS_SEARCH_URL, params=params, timeout=30)
        response.raise_for_status()
        
        return OpenFoodFactsResponse(success=True, data=response.json())
        
    except requests.RequestException as e:
        logger.error(f"OpenFoodFacts API error: {str(e)}")
        return OpenFoodFactsResponse(success=False, error_message=f"API request failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return OpenFoodFactsResponse(success=False, error_message=f"Unexpected error: {str(e)}")


def get_product_api(product_code: str) -> OpenFoodFactsResponse:
    """Get single product from OpenFoodFacts API"""
    try:
        url = f"{OPENFOODFACTS_PRODUCT_URL}/{product_code}.json"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('status') == 1 and data.get('product'):
            return OpenFoodFactsResponse(success=True, data=data.get('product'))
        else:
            return OpenFoodFactsResponse(success=False, error_message="Product not found")
            
    except requests.RequestException as e:
        logger.error(f"Product API error: {str(e)}")
        return OpenFoodFactsResponse(success=False, error_message=f"API request failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return OpenFoodFactsResponse(success=False, error_message=f"Unexpected error: {str(e)}")


# View Functions
@api_view(['GET'])
@permission_classes([AllowAny])
def product_search(request):
    """
    Enhanced product search with ML-based personalized scoring
    """
    try:
        # Validate input parameters
        serializer = ProductSearchSerializer(data=request.GET)
        if not serializer.is_valid():
            return Response({
                'error': 'Invalid search parameters',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        validated_data = serializer.validated_data
        query = validated_data.get('query', '')
        page = validated_data.get('page', 1)
        page_size = validated_data.get('page_size', 20)
        sort_by = validated_data.get('sort_by', 'relevance')
        include_personalized = validated_data.get('include_personalized_scores', True)
        
        # Generate cache key
        cache_params = {
            'query': query,
            'page': page,
            'page_size': page_size,
            'sort_by': sort_by,
            'user_id': request.user.id if request.user.is_authenticated else 0
        }
        cache_key = generate_cache_key("enhanced_search", request.user.id if request.user.is_authenticated else 0, cache_params)
        
        # Check cache
        cached_result = cache.get(cache_key)
        if cached_result:
            return Response(cached_result, status=status.HTTP_200_OK)
        
        # Build search filters
        filters = {}
        filter_mapping = {
            'category': 'categories_tags',
            'brand': 'brands_tags',
            'nutriscore_grade': 'nutriscore_grade',
            'nova_group': 'nova_group',
        }
        
        for param, filter_key in filter_mapping.items():
            value = request.GET.get(param)
            if value:
                filters[filter_key] = value
        
        # Search products via OpenFoodFacts API
        search_response = search_products_api(
            query=query,
            filters=filters,
            page=page,
            page_size=page_size
        )
        
        if not search_response.success:
            return Response({
                'error': search_response.error_message or 'Search failed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        search_data = search_response.data
        products = search_data.get('products', [])
        
        # Process products
        processed_products = []
        for product in products:
            serialized_product = OpenFoodFactsProductSerializer.serialize(product)
            if serialized_product:
                processed_products.append(serialized_product)
        
        # Add ML-based personalized scores for authenticated users
        if request.user.is_authenticated and include_personalized and processed_products:
            try:
                user_profile = get_user_profile_data(request.user)
                
                # Add ML analysis for first 10 products
                for i, product in enumerate(processed_products[:10]):
                    try:
                        product_code = product.get('code')
                        if product_code:
                            # Try to get ML score directly from service
                            try:
                                score_result = ml_product_score_service.get_personalized_score(
                                    user_profile, product_code
                                )
                                if score_result:
                                    product['ml_analysis'] = {
                                        'personalized_score': score_result.get('personalized_score', 5.0),
                                        'score_level': score_result.get('score_level', {}),
                                        'has_ml_analysis': True,
                                        'analysis_summary': score_result.get('analysis', {})
                                    }
                                else:
                                    # Fallback to basic rule-based analysis for warnings
                                    analyzer = ProductAnalyzer()
                                    warnings_result = analyzer.analyze_warnings_only(product, user_profile)
                                    product['ml_analysis'] = {
                                        'basic_warnings': warnings_result.get('warnings', [])[:2],
                                        'critical_issues': warnings_result.get('critical_issues', 0),
                                        'has_ml_analysis': False
                                    }
                            except Exception as e:
                                logger.warning(f"ML score error for {product_code}: {str(e)}")
                                # Use rule-based warnings as fallback
                                analyzer = ProductAnalyzer()
                                warnings_result = analyzer.analyze_warnings_only(product, user_profile)
                                product['ml_analysis'] = {
                                    'basic_warnings': warnings_result.get('warnings', [])[:2],
                                    'has_ml_analysis': False,
                                    'error': 'ML analysis failed'
                                }
                    except Exception as e:
                        logger.warning(f"Product analysis error for {product.get('code')}: {str(e)}")
                        product['ml_analysis'] = {'error': 'Analysis failed'}
                        
            except Exception as e:
                logger.error(f"ML analysis error: {str(e)}")
                # Continue without ML analysis
        
        # Sort products if ML scores are available
        if sort_by == 'personalized_score' and request.user.is_authenticated:
            processed_products.sort(
                key=lambda x: x.get('ml_analysis', {}).get('personalized_score', 0), 
                reverse=True
            )
        
        # Prepare response
        response_data = {
            'products': processed_products,
            'meta': {
                'page': page,
                'page_size': page_size,
                'total_results': search_data.get('count', 0),
                'sort_by': sort_by,
                'has_ml_analysis': request.user.is_authenticated and include_personalized,
                'cache_used': False
            }
        }
        
        # Cache results for 3 minutes
        cache.set(cache_key, response_data, 180)
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return Response({
            'error': f'Search failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_product_detail(request, product_code):
    """
    Get product details from OpenFoodFacts API
    """
    try:
        # Check cache
        cache_key = f"product_detail_{product_code}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return Response(cached_result, status=status.HTTP_200_OK)
        
        # Get from API
        api_response = get_product_api(product_code)
        if not api_response.success:
            return Response({
                'error': 'Product not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        product_data = OpenFoodFactsProductSerializer.serialize(api_response.data)
        
        # Cache for 30 minutes
        cache.set(cache_key, product_data, 1800)
        
        return Response(product_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Product detail error: {str(e)}")
        return Response({
            'error': f'Failed to get product: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analyze_product_complete(request):
    """
    Complete product analysis - ML skorları + kural tabanlı uyarılar
    """
    try:
        product_code = request.data.get('product_code')
        if not product_code:
            return Response({
                'error': 'Product code is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check cache
        cache_key = f"complete_analysis_{request.user.id}_{product_code}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return Response(cached_result, status=status.HTTP_200_OK)
        
        # Get user profile
        user_profile = get_user_profile_data(request.user)
        
        # Get product from OpenFoodFacts API
        api_response = get_product_api(product_code)
        if not api_response.success:
            return Response({
                'error': 'Product not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        product_data = api_response.data
        serialized_product = OpenFoodFactsProductSerializer.serialize(product_data)
        
        # ML tabanlı skor hesaplama (doğrudan servis)
        ml_score_result = ml_product_score_service.get_personalized_score(user_profile, product_code)
        
        # Kural tabanlı uyarılar (ProductAnalyzer)
        analyzer = ProductAnalyzer()
        warnings_result = analyzer.analyze_warnings_only(product_data, user_profile)
        
        # Sonuçları birleştir
        analysis_result = {
            'ml_analysis': ml_score_result if ml_score_result else {
                'personalized_score': 5.0,
                'score_level': {'level': 'medium', 'description': 'Orta seviye'},
                'analysis': {'note': 'ML analizi yapılamadı'}
            },
            'rule_based_warnings': warnings_result,
            'combined_summary': {
                'has_ml_score': ml_score_result is not None,
                'ml_score': ml_score_result.get('personalized_score', 5.0) if ml_score_result else 5.0,
                'critical_warnings': warnings_result.get('critical_issues', 0),
                'total_warnings': len(warnings_result.get('warnings', [])),
                'recommendation': 'suitable' if (ml_score_result.get('personalized_score', 5.0) >= 6.0 if ml_score_result else True) and warnings_result.get('critical_issues', 0) == 0 else 'caution'
            }
        }
        
        response_data = {
            'product': serialized_product,
            'analysis': analysis_result,
            'user_profile_used': {
                'has_conditions': bool(user_profile.get('medical_conditions')),
                'has_allergies': bool(user_profile.get('allergies')),
                'has_goals': bool(user_profile.get('health_goals'))
            }
        }
        
        # Cache for 10 minutes
        cache.set(cache_key, response_data, 600)
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Complete analysis error: {str(e)}")
        return Response({
            'error': f'Analysis failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_personalized_product_score(request):
    """
    Get ML-based personalized score for a specific product (doğrudan ML servis)
    """
    try:
        product_code = request.GET.get('product_code')
        
        if not product_code:
            return Response({
                'error': 'product_code parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check cache
        cache_key = f"ml_personalized_score_{request.user.id}_{product_code}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return Response(cached_result, status=status.HTTP_200_OK)
        
        # Get user profile
        user_profile = get_user_profile_data(request.user)
        
        # Calculate ML-based personalized score (doğrudan servis çağrısı)
        score_result = ml_product_score_service.get_personalized_score(user_profile, product_code)
        
        if not score_result:
            return Response({
                'error': 'Product not found or ML analysis failed'
            }, status=status.HTTP_404_NOT_FOUND)
        
        response_data = {
            'personalized_score': score_result.get('personalized_score', 5.0),
            'score_level': score_result.get('score_level', {}),
            'analysis': score_result.get('analysis', {}),
            'product_info': score_result.get('product_info', {}),
            'ml_model_used': True
        }
        
        # Cache for 10 minutes
        cache.set(cache_key, response_data, 600)
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Personalized score error: {str(e)}")
        return Response({
            'error': f'Failed to calculate personalized score: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_ml_recommendations(request):
    """
    ML tabanlı ürün önerisi (doğrudan recommendation servis)
    """
    try:
        # User profile verilerini al
        user_profile = get_user_profile_data(request.user)
        
        # Kullanıcı profil verilerinin formatını kontrol et
        if not isinstance(user_profile, dict):
            return Response({
                'error': 'Invalid user profile data'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Parameters
        limit = int(request.GET.get('limit', 6))
        min_score = float(request.GET.get('min_score', 6.0))
        product_code = request.GET.get('product_code', None)
        categories = request.GET.get('categories', None)
        
        # Cache key
        cache_key = generate_cache_key(
            "ml_recommendation_direct",
            request.user.id,
            {
                'product_code': product_code, 
                'categories': categories, 
                'limit': limit, 
                'min_score': min_score
            }
        )
        
        cached_result = cache.get(cache_key)
        if cached_result:
            return Response(cached_result, status=status.HTTP_200_OK)
        
        # Product-based alternatives
        if product_code:
            result = ml_recommendation_service.get_product_alternatives(
                user_profile=user_profile,
                product_code=product_code,
                limit=limit,
                min_score_threshold=min_score
            )
            
            if not result:
                return Response({
                    'error': 'No alternatives found or invalid product'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Serialize alternatives
            alternatives_data = []
            for alt in result['alternatives']:
                product_data = alt['product']
                # ML skorlarını product objesine ekle
                ml_attributes = [
                    'final_score', 'ml_score', 'target_score', 'score_improvement',
                    'similarity_bonus', 'improvement_bonus', 'reason', 'category_match'
                ]
                for attr in ml_attributes:
                    if attr in alt:
                        setattr(product_data, attr, alt[attr])
                alternatives_data.append(product_data)
            
            response_data = {
                'type': 'alternatives',
                'alternatives': ProductRecommendationSerializer(alternatives_data, many=True).data,
                'target_product': result['target_product'],
                'recommendation_stats': result['recommendation_stats'],
                'ml_service_used': True,
                'user_id': request.user.id
            }
        
        # General personalized recommendations
        else:
            result = ml_recommendation_service.get_user_recommendations(
                user_data=user_profile,
                categories=categories,
                limit=limit
            )
            
            if not result or not result.get('recommendations'):
                return Response({
                    'error': 'No recommendations found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Serialize recommendations
            recommendations_data = []
            for rec in result['recommendations']:
                product_data = rec['product']
                # ML skorlarını product objesine ekle
                ml_attributes = [
                    'final_score', 'ml_score', 'personalization_bonus', 
                    'recommendation_reason', 'health_benefits'
                ]
                for attr in ml_attributes:
                    if attr in rec:
                        setattr(product_data, attr, rec[attr])
                recommendations_data.append(product_data)
            
            response_data = {
                'type': 'personalized',
                'recommendations': ProductRecommendationSerializer(recommendations_data, many=True).data,
                'user_profile_summary': result.get('user_profile_summary', {}),
                'recommendation_stats': result.get('recommendation_stats', {}),
                'ml_service_used': True,
                'user_id': request.user.id
            }
        
        # Cache for 5 minutes
        cache.set(cache_key, response_data, 300)
        return Response(response_data, status=status.HTTP_200_OK)
    
    except ValueError as e:
        logger.error(f"Parameter validation error: {e}")
        return Response({
            'error': 'Invalid parameters provided'
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"ML recommendation error: {e}")
        return Response({
            'error': f'Failed to get recommendations: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_product_warnings_only(request):
    """
    Get quick product warnings only (sadece kural tabanlı uyarılar)
    """
    try:
        product_code = request.GET.get('product_code')
        
        if not product_code:
            return Response({
                'error': 'product_code parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check cache
        cache_key = f"warnings_only_{request.user.id}_{product_code}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return Response(cached_result, status=status.HTTP_200_OK)
        
        # Get user profile and product
        user_profile = get_user_profile_data(request.user)
        
        # Get product from API
        api_response = get_product_api(product_code)
        if not api_response.success:
            return Response({
                'error': 'Product not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Use ProductAnalyzer for warnings-only analysis (sadece kural tabanlı)
        analyzer = ProductAnalyzer()
        warnings_result = analyzer.analyze_warnings_only(api_response.data, user_profile)
        
        # Add analysis method info
        warnings_result['analysis_method'] = 'rule_based_only'
        warnings_result['ml_analysis_available'] = False
        
        # Cache for 5 minutes
        cache.set(cache_key, warnings_result, 300)
        
        return Response(warnings_result, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Product warnings error: {str(e)}")
        return Response({
            'error': f'Failed to get product warnings: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def compare_products(request):
    """
    Compare multiple products with ML-based personalized scoring
    """
    try:
        # Validate input
        serializer = ProductComparisonSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'error': 'Invalid parameters',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        product_codes = serializer.validated_data['product_codes']
        
        # Check cache
        cache_key = generate_cache_key(
            "product_comparison", 
            request.user.id, 
            {'products': sorted(product_codes)}
        )
        cached_result = cache.get(cache_key)
        if cached_result:
            return Response(cached_result, status=status.HTTP_200_OK)
        
        # Get user profile
        user_profile = get_user_profile_data(request.user)
        
        # Get and score products
        compared_products = []
        for product_code in product_codes:
            try:
                # Try to get from database first for ML analysis
                try:
                    db_product = ProductFeatures.objects.get(
                        product_code=product_code,
                        is_valid_for_analysis=True
                    )
                    
                    # Calculate ML score
                    score_result = ml_product_score_service.get_personalized_score(user_profile, product_code)
                    
                    # Add ML scores to product
                    db_product.final_score = score_result.get('personalized_score', 5.0) if score_result else 5.0
                    db_product.ml_analysis = score_result.get('analysis', {}) if score_result else {}
                    
                    compared_products.append(db_product)
                    
                except ProductFeatures.DoesNotExist:
                    # Get from API and do basic analysis
                    api_response = get_product_api(product_code)
                    if api_response.success:
                        # Create a temporary product-like object
                        temp_product = type('TempProduct', (), {})()
                        temp_product.product_code = product_code
                        temp_product.product_name = api_response.data.get('product_name', '')
                        temp_product.main_category = api_response.data.get('categories', '').split(',')[0] if api_response.data.get('categories') else ''
                        
                        # Basic scoring using ProductAnalyzer
                        analyzer = ProductAnalyzer()
                        basic_analysis = analyzer.analyze_product_complete(api_response.data, user_profile)
                        temp_product.final_score = basic_analysis.get('health_score', 50) / 10.0  # Convert to 0-10 scale
                        temp_product.ml_analysis = {'basic_analysis': True}
                        
                        compared_products.append(temp_product)
                        
            except Exception as e:
                logger.warning(f"Product comparison error for {product_code}: {str(e)}")
                continue
        
        if not compared_products:
            return Response({
                'error': 'No valid products found for comparison'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Sort by score
        compared_products.sort(key=lambda x: getattr(x, 'final_score', 0), reverse=True)
        
        # Create comparison summary
        scores = [getattr(p, 'final_score', 0) for p in compared_products]
        comparison_summary = {
            'best_product': {
                'code': compared_products[0].product_code,
                'name': getattr(compared_products[0], 'product_name', ''),
                'score': compared_products[0].final_score
            },
            'score_range': {
                'highest': max(scores),
                'lowest': min(scores),
                'average': round(sum(scores) / len(scores), 2)
            },
            'products_compared': len(compared_products)
        }
        
        response_data = {
            'products': ProductRecommendationSerializer(compared_products, many=True).data,
            'comparison_summary': comparison_summary,
            'best_match': comparison_summary['best_product']
        }
        
        # Cache for 5 minutes
        cache.set(cache_key, response_data, 300)
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Product comparison error: {str(e)}")
        return Response({
            'error': f'Failed to compare products: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)