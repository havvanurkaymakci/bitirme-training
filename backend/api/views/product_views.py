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

# AI Models
from aimodels.product_analysis import ProductAnalyzer
from aimodels.ml_models.recommendation_service import ml_recommendation_service
from aimodels.ml_models.ml_product_score_service import ml_product_score_service

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
        return get_user_profile_data.__defaults__[0] if hasattr(get_user_profile_data, '__defaults__') else {}


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
                
                # Add quick analysis for first 10 products
                for i, product in enumerate(processed_products[:10]):
                    try:
                        product_code = product.get('code')
                        if product_code:
                            # Try to get from our database first
                            try:
                                db_product = ProductFeatures.objects.get(
                                    product_code=product_code, 
                                    is_valid_for_analysis=True
                                )
                                # Use ML scoring service
                                score_result = ml_product_score_service.calculate_personalized_score(
                                    user_profile, db_product
                                )
                                product['ml_analysis'] = {
                                    'personalized_score': score_result.get('personalized_score', 5.0),
                                    'score_level': score_result.get('score_level', {}),
                                    'has_analysis': True
                                }
                            except ProductFeatures.DoesNotExist:
                                # Use basic analysis for non-database products
                                analyzer = ProductAnalyzer()
                                basic_analysis = analyzer.analyze_quick(product, user_profile)
                                product['ml_analysis'] = {
                                    'basic_health_score': basic_analysis.get('basic_health_score', 5.0),
                                    'critical_alerts': basic_analysis.get('critical_alerts', [])[:2],
                                    'has_analysis': False
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
    Enhanced product detail with ML-based health analysis
    """
    try:
        cache_key = f"enhanced_product_detail_{product_code}_{request.user.id if request.user.is_authenticated else 0}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return JsonResponse(cached_result, safe=False)
        
        # Get product from OpenFoodFacts API
        api_response = get_product_api(product_code)
        if not api_response.success:
            return JsonResponse({
                'error': api_response.error_message or 'Product not found'
            }, status=404)

        # Format response data
        product_data = {
            'product': api_response.data,
            'status': 1,
            'status_verbose': 'product found'
        }

        if request.user.is_authenticated:
            try:
                user_profile = get_user_profile_data(request.user)

                try:
                    db_product = ProductFeatures.objects.get(
                        product_code=product_code,
                        is_valid_for_analysis=True
                    )

                    analysis_cache_key = f"ml_detailed_analysis_{request.user.id}_{product_code}"
                    cached_analysis = cache.get(analysis_cache_key)

                    if cached_analysis:
                        product_data['ml_analysis'] = cached_analysis
                    else:
                        score_result = ml_product_score_service.calculate_personalized_score(user_profile, db_product)

                        ml_analysis = {
                            'personalized_score': score_result.get('personalized_score', 5.0),
                            'score_level': score_result.get('score_level', {}),
                            'analysis': score_result.get('analysis', {}),
                            'has_ml_analysis': True,
                            'analysis_type': 'detailed_ml'
                        }

                        cache.set(analysis_cache_key, ml_analysis, 600)
                        product_data['ml_analysis'] = ml_analysis

                except ProductFeatures.DoesNotExist:
                    analyzer = ProductAnalyzer()
                    detailed_analysis = analyzer.analyze_detailed(api_response.data, user_profile)

                    # 🔧 BURADA serializer ile wrap ediyoruz
                    serializer = HealthAnalysisSerializer(detailed_analysis)
                    product_data['user_analysis'] = serializer.data
                    product_data['analysis_type'] = 'rule_based'

            except Exception as e:
                logger.warning(f"Product analysis error: {str(e)}")
                product_data['analysis_error'] = str(e)

        cache.set(cache_key, product_data, 600)

        return JsonResponse(product_data, safe=False)

    except Exception as e:
        logger.error(f"Product detail error: {str(e)}")
        return JsonResponse({
            'error': f'Failed to get product details: {str(e)}'
        }, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_personalized_product_score(request):
    """
    Get ML-based personalized score for a specific product
    """
    try:
        # Get product_code from query parameters
        product_code = request.GET.get('product_code')

        # Validate required parameter
        if not product_code:
            return Response({
                'error': 'product_code parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check cache
        cache_key = f"ml_personalizedscore_{request.user.id}_{product_code}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return Response(cached_result, status=status.HTTP_200_OK)

        # Get user profile and product
        user_profile = get_user_profile_data(request.user)
        
        # Calculate ML-based personalized score using ml_score_service
        score_result = ml_product_score_service.get_personalized_score(user_profile, product_code)

        if not score_result:
            return Response({
                'error': 'Product not found or analysis failed'
            }, status=status.HTTP_404_NOT_FOUND)

        # Format response
        response_data = {
            'personalized_score': score_result.get('personalized_score', 5.0),
            'score_level': score_result.get('score_level', {}),
            'analysis': score_result.get('analysis', {}),
            'product_info': score_result.get('product_info', {})
        }

        # Cache for 10 minutes
        cache.set(cache_key, response_data, 600)

        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Personalized score error: {str(e)}")
        return Response({
            'error': f'Failed to calculate personalized score: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Yardımcı fonksiyonlar

def _calculate_search_relevance(product_data: Dict) -> float:
    """
    Arama sonucu için relevans skoru hesapla
    """
    try:
        base_score = 5.0
        
        # Nutriscore bonus
        nutriscore = product_data.get('nutriscore_grade', '').lower()
        nutriscore_bonus = {'a': 2.0, 'b': 1.5, 'c': 1.0, 'd': 0.5, 'e': 0.0}
        base_score += nutriscore_bonus.get(nutriscore, 0)
        
        # Veri tamlığı bonus
        completeness = product_data.get('completeness', 0)
        if completeness > 80:
            base_score += 1.0
        elif completeness > 60:
            base_score += 0.5
        
        # NOVA skoru ayarlaması
        nova_group = product_data.get('nova_group', 2)
        if nova_group == 1:
            base_score += 1.0
        elif nova_group == 4:
            base_score -= 1.0
        
        # Son güncellenme zamanı bonus (yeni ürünler)
        last_modified = product_data.get('last_modified_t', 0)
        if last_modified and last_modified > 1640995200:  # 2022'den sonra
            base_score += 0.5
        
        return max(1.0, min(10.0, base_score))
        
    except Exception as e:
        logger.error(f"Relevans skoru hatası: {str(e)}")
        return 5.0
# Eksik metotlar - product_views.py dosyasına eklenecek

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analyze_product_complete(request):
    """
    Complete product analysis with ML-based personalized recommendations
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
        
        # Try ML analysis first
        ml_analysis = None
        try:
            db_product = ProductFeatures.objects.get(
                product_code=product_code,
                is_valid_for_analysis=True
            )
            
            # Use ML scoring service
            score_result = ml_product_score_service.calculate_personalized_score(user_profile, db_product)
            ml_analysis = {
                'personalized_score': score_result.get('personalized_score', 5.0),
                'score_level': score_result.get('score_level', {}),
                'analysis': score_result.get('analysis', {}),
                'has_ml_analysis': True
            }
        except ProductFeatures.DoesNotExist:
            pass
        
        # Use ProductAnalyzer for comprehensive analysis
        analyzer = ProductAnalyzer()
        detailed_analysis = analyzer.analyze_detailed(product_data, user_profile)
        
        response_data = {
            'product': product_data,
            'analysis': detailed_analysis,
            'ml_analysis': ml_analysis,
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
def get_personalized_warnings(request):
    """
    Get personalized warnings for a product based on user profile
    """
    try:
        product_code = request.data.get('product_code')
        if not product_code:
            return Response({
                'error': 'Product code is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check cache
        cache_key = f"personalized_warnings_{request.user.id}_{product_code}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return Response(cached_result, status=status.HTTP_200_OK)
        
        # Get user profile
        user_profile = get_user_profile_data(request.user)
        
        # Get product from API
        api_response = get_product_api(product_code)
        if not api_response.success:
            return Response({
                'error': 'Product not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Use ProductAnalyzer to get personalized warnings
        analyzer = ProductAnalyzer()
        warnings = analyzer.get_personalized_warnings(api_response.data, user_profile)
        
        response_data = {
            'product_code': product_code,
            'warnings': warnings,
            'warning_count': len(warnings),
            'severity_breakdown': {
                'critical': len([w for w in warnings if w.get('severity') == 'critical']),
                'warning': len([w for w in warnings if w.get('severity') == 'warning']),
                'info': len([w for w in warnings if w.get('severity') == 'info'])
            }
        }
        
        # Cache for 5 minutes
        cache.set(cache_key, response_data, 300)
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Personalized warnings error: {str(e)}")
        return Response({
            'error': f'Failed to get warnings: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_product_warnings_only(request):
    """
    Sadece ürün uyarıları döndür
    """
    try:
        product_code = request.GET.get('product_code')
        
        if not product_code:
            return Response({
                'error': 'product_code parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        user_profile = get_user_profile_data(request.user)
        
        try:
            product = ProductFeatures.objects.get(
                product_code=product_code,
                is_valid_for_analysis=True
            )
        except ProductFeatures.DoesNotExist:
            return Response({
                'error': 'Product not found'
            }, status=status.HTTP_404_NOT_FOUND)

        # Uyarıları hesapla
        warnings = []
        
        # Sağlık durumu uyarıları
        conditions = user_profile.get('medical_conditions', [])
        if 'diabetes_type_2' in conditions and product.get_sugar() > 10:
            warnings.append({
                'type': 'medical',
                'level': 'high',
                'message': 'Yüksek şeker içeriği - Diyabet hastası için riskli'
            })
        
        if 'hypertension' in conditions and product.get_salt() > 1.5:
            warnings.append({
                'type': 'medical',
                'level': 'high',
                'message': 'Yüksek tuz içeriği - Hipertansiyon hastası için riskli'
            })

        # Alerji uyarıları
        allergies = user_profile.get('allergies', [])
        product_allergens = product.get_allergens()
        for allergen in allergies:
            if allergen.lower() in product_allergens.lower():
                warnings.append({
                    'type': 'allergy',
                    'level': 'critical',
                    'message': f'Alerjen içeriyor: {allergen}'
                })

        # Genel sağlık uyarıları
        if product.processing_level >= 4:
            warnings.append({
                'type': 'processing',
                'level': 'medium',
                'message': 'Yüksek işlenmişlik seviyesi'
            })

        if product.has_risky_additives():
            warnings.append({
                'type': 'additives',
                'level': 'medium',
                'message': 'Riskli katkı maddeleri içeriyor'
            })

        response_data = {
            'product_code': product_code,
            'warnings': warnings,
            'total_warnings': len(warnings),
            'risk_level': 'high' if any(w['level'] == 'critical' for w in warnings) else 
                         'medium' if any(w['level'] == 'high' for w in warnings) else 'low'
        }

        return Response(response_data, status=status.HTTP_200_OK)

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
                # Try to get from database first
                try:
                    db_product = ProductFeatures.objects.get(
                        product_code=product_code,
                        is_valid_for_analysis=True
                    )
                    
                    # Calculate ML score
                    score_result = ml_product_score_service.calculate_personalized_score(user_profile, db_product)
                    
                    # Add ML scores to product
                    db_product.final_score = score_result.get('personalized_score', 5.0)
                    db_product.ml_analysis = score_result.get('analysis', {})
                    
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
                        
                        # Basic scoring
                        analyzer = ProductAnalyzer()
                        basic_analysis = analyzer.analyze_quick(api_response.data, user_profile)
                        temp_product.final_score = basic_analysis.get('basic_health_score', 5.0)
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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_health_analysis(request, product_code):
    """
    Get comprehensive health analysis for a product
    Combines ML-based analysis (when available) with rule-based analysis
    """
    try:
        # Check cache
        cache_key = f"health_analysis_{request.user.id}_{product_code}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return Response(cached_result, status=status.HTTP_200_OK)
        
        # Get user profile
        user_profile = get_user_profile_data(request.user)
        
        # Initialize response data structure
        response_data = {
            'product': {},
            'personalized_score': 5.0,
            'score_level': {},
            'positive_points': [],
            'negative_points': [],
            'recommendations': [],
            'health_alerts': [],
            'analysis_type': 'rule_based',
            'confidence_score': 0,
            'nutritional_analysis': {},
            'allergen_alerts': [],
            'medical_alerts': [],
            'dietary_compliance': {}
        }
        
        # Try to get from database for ML-based analysis
        ml_analysis_available = False
        try:
            db_product = ProductFeatures.objects.get(
                product_code=product_code,
                is_valid_for_analysis=True
            )
            
            # Calculate ML-based analysis
            score_result = ml_product_score_service.calculate_personalized_score(user_profile, db_product)
            analysis_data = score_result.get('analysis', {})
            
            # Update response with ML data
            response_data.update({
                'product': ProductFeaturesBaseSerializer(db_product).data,
                'personalized_score': score_result.get('personalized_score', 5.0),
                'score_level': score_result.get('score_level', {}),
                'positive_points': analysis_data.get('positive_points', []),
                'negative_points': analysis_data.get('negative_points', []),
                'recommendations': analysis_data.get('recommendations', []),
                'analysis_type': 'ml_based',
                'confidence_score': score_result.get('confidence_score', 85)
            })
            
            ml_analysis_available = True
            
        except ProductFeatures.DoesNotExist:
            ml_analysis_available = False
        
        # Always get rule-based analysis for comprehensive coverage
        api_response = get_product_api(product_code)
        if not api_response.success:
            if not ml_analysis_available:
                return Response({
                    'error': 'Product not found'
                }, status=status.HTTP_404_NOT_FOUND)
        else:
            # Use ProductAnalyzer for rule-based analysis
            analyzer = ProductAnalyzer()
            
            # Get comprehensive analysis using existing methods
            rule_based_analysis = analyzer.analyze_product_complete(api_response.data, user_profile)
            
            if not ml_analysis_available:
                # Use rule-based analysis as primary
                response_data.update({
                    'product': {
                        'product_code': product_code,
                        'product_name': api_response.data.get('product_name', ''),
                        'product_name_tr': api_response.data.get('product_name_tr', ''),
                        'image_url': api_response.data.get('image_url', ''),
                        'brands': api_response.data.get('brands', ''),
                        'categories': api_response.data.get('categories', ''),
                        'nutriscore_grade': api_response.data.get('nutriscore_grade', ''),
                        'nova_group': api_response.data.get('nova_group', 0)
                    },
                    'personalized_score': rule_based_analysis.get('health_score', 50) / 10.0,  # Convert to 0-10 scale
                    'score_level': _get_score_level(rule_based_analysis.get('health_score', 50)),
                    'positive_points': _extract_positive_points(rule_based_analysis),
                    'negative_points': _extract_negative_points(rule_based_analysis),
                    'recommendations': rule_based_analysis.get('recommendations', []),
                    'analysis_type': 'rule_based',
                    'confidence_score': rule_based_analysis.get('confidence_score', 70)
                })
            else:
                # Combine ML and rule-based analysis
                response_data.update({
                    'analysis_type': 'hybrid',
                    'rule_based_backup': {
                        'health_score': rule_based_analysis.get('health_score', 50),
                        'warnings': rule_based_analysis.get('warnings', []),
                        'recommendations': rule_based_analysis.get('recommendations', [])
                    }
                })
            
            # Always include detailed health information from rule-based analysis
            response_data.update({
                'health_alerts': rule_based_analysis.get('health_alerts', []),
                'nutritional_analysis': rule_based_analysis.get('nutritional_analysis', {}),
                'allergen_alerts': rule_based_analysis.get('allergen_alerts', []),
                'medical_alerts': rule_based_analysis.get('medical_alerts', []),
                'dietary_compliance': rule_based_analysis.get('dietary_compliance', {}),
                'is_suitable': rule_based_analysis.get('is_suitable', True),
                'summary': rule_based_analysis.get('summary', ''),
                'analysis_timestamp': rule_based_analysis.get('analysis_timestamp', '')
            })
        
        # Cache for 10 minutes
        cache.set(cache_key, response_data, 600)
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Health analysis error: {str(e)}")
        return Response({
            'error': f'Failed to get health analysis: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _get_score_level(health_score):
    """Convert health score to score level"""
    if health_score >= 80:
        return {'level': 'excellent', 'color': 'green', 'description': 'Mükemmel'}
    elif health_score >= 60:
        return {'level': 'good', 'color': 'lightgreen', 'description': 'İyi'}
    elif health_score >= 40:
        return {'level': 'fair', 'color': 'yellow', 'description': 'Orta'}
    elif health_score >= 20:
        return {'level': 'poor', 'color': 'orange', 'description': 'Zayıf'}
    else:
        return {'level': 'very_poor', 'color': 'red', 'description': 'Çok Zayıf'}


def _extract_positive_points(analysis):
    """Extract positive points from rule-based analysis"""
    positive_points = []
    
    # Nutritional analysis positive points
    nutritional = analysis.get('nutritional_analysis', {})
    health_markers = nutritional.get('health_markers', {})
    
    if health_markers.get('good_protein'):
        positive_points.append({
            'category': 'nutrition',
            'point': 'Yüksek protein içeriği',
            'description': 'Protein ihtiyacınızı karşılamaya yardımcı olur'
        })
    
    if health_markers.get('good_fiber'):
        positive_points.append({
            'category': 'nutrition',
            'point': 'Yüksek lif içeriği',
            'description': 'Sindirim sağlığınızı destekler'
        })
    
    if not health_markers.get('high_sugar'):
        positive_points.append({
            'category': 'nutrition',
            'point': 'Düşük şeker içeriği',
            'description': 'Kan şekeri dengenizi korur'
        })
    
    if not health_markers.get('high_sodium'):
        positive_points.append({
            'category': 'nutrition',
            'point': 'Düşük sodyum içeriği',
            'description': 'Kalp sağlığınızı destekler'
        })
    
    # Quality rating positive points
    quality_rating = nutritional.get('quality_rating', '')
    if quality_rating in ['excellent', 'good']:
        positive_points.append({
            'category': 'quality',
            'point': 'Yüksek beslenme kalitesi',
            'description': 'Genel beslenme değeri yüksek'
        })
    
    return positive_points


def _extract_negative_points(analysis):
    """Extract negative points from rule-based analysis"""
    negative_points = []
    
    # From warnings
    warnings = analysis.get('warnings', [])
    for warning in warnings:
        negative_points.append({
            'category': warning.get('category', 'general'),
            'point': warning.get('title', warning.get('message', '')),
            'description': warning.get('description', warning.get('details', '')),
            'severity': warning.get('severity', 'medium')
        })
    
    # From health markers
    nutritional = analysis.get('nutritional_analysis', {})
    health_markers = nutritional.get('health_markers', {})
    
    if health_markers.get('high_sugar'):
        negative_points.append({
            'category': 'nutrition',
            'point': 'Yüksek şeker içeriği',
            'description': 'Kan şekeri seviyenizi yükseltebilir',
            'severity': 'medium'
        })
    
    if health_markers.get('high_sodium'):
        negative_points.append({
            'category': 'nutrition',
            'point': 'Yüksek sodyum içeriği',
            'description': 'Tansiyon problemlerine yol açabilir',
            'severity': 'medium'
        })
    
    if health_markers.get('high_saturated_fat'):
        negative_points.append({
            'category': 'nutrition',
            'point': 'Yüksek doymuş yağ içeriği',
            'description': 'Kolesterol seviyenizi etkileyebilir',
            'severity': 'medium'
        })
    
    return negative_points

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_ml_recommendations(request):
    """
    ML tabanlı ürün önerisi: 
    - Eğer product_code verilmişse -> alternatif ürünler
    - Verilmemişse -> kişiselleştirilmiş öneriler
    """
    try:
        user_profile = get_user_profile_data(request.user)

        # Ortak parametreler
        limit = int(request.GET.get('limit', 6))
        min_score = float(request.GET.get('min_score', 6.0))
        product_code = request.GET.get('product_code', None)
        categories = request.GET.get('categories', None)

        # Cache key oluştur
        cache_key = generate_cache_key(
            "ml_recommendation_combined",
            request.user.id,
            {'product_code': product_code, 'categories': categories, 'limit': limit, 'min_score': min_score}
        )
        cached_result = cache.get(cache_key)
        if cached_result:
            return Response(cached_result, status=status.HTTP_200_OK)

        # 1️⃣ Ürün bazlı alternatif önerisi
        if product_code:
            result = ml_recommendation_service.get_product_alternatives(
                user_profile=user_profile,
                product_code=product_code,
                limit=limit,
                min_score_threshold=min_score
            )

            if not result:
                return Response({'error': 'Alternatif bulunamadı veya ürün geçersiz'}, status=status.HTTP_404_NOT_FOUND)

            # ML skor bilgilerini modele göm
            alternatives_data = []
            for alt in result['alternatives']:
                product_data = alt['product']
                # Modele ML skorlarını ekle
                for key in ['final_score', 'ml_score', 'target_score', 'score_improvement',
                            'similarity_bonus', 'improvement_bonus', 'reason', 'category_match']:
                    setattr(product_data, key, alt[key])
                alternatives_data.append(product_data)

            response_data = {
                'type': 'alternatives',
                'alternatives': ProductRecommendationSerializer(alternatives_data, many=True).data,
                'target_product': result['target_product'],
                'recommendation_stats': result['recommendation_stats']
            }

        # 2️⃣ Genel kişiselleştirilmiş öneri
        else:
            result = ml_recommendation_service.get_user_recommendations(
                user_data=user_profile,
                categories=categories,
                limit=limit
            )

            if not result or not result.get('recommendations'):
                return Response({'error': 'Öneri bulunamadı'}, status=status.HTTP_404_NOT_FOUND)

            recommendations_data = []
            for rec in result['recommendations']:
                product_data = rec['product']
                # Modele ML skorlarını ekle
                for key in ['final_score', 'ml_score', 'personalization_bonus', 'recommendation_reason', 'health_benefits']:
                    if key in rec:
                        setattr(product_data, key, rec[key])
                recommendations_data.append(product_data)

            response_data = {
                'type': 'personalized',
                'recommendations': ProductRecommendationSerializer(recommendations_data, many=True).data,
                'user_profile_summary': result.get('user_profile_summary', {}),
                'recommendation_stats': result.get('recommendation_stats', {})
            }

        # Cache'e yaz
        cache.set(cache_key, response_data, 300)
        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"ML öneri hatası: {e}")
        return Response({'error': f'Öneri alınamadı: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

"""
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_product_alternatives(request):
    
    try:
        # Validate input
        serializer = ProductAlternativesSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'error': 'Invalid parameters',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        validated_data = serializer.validated_data
        product_code = validated_data['product_code']
        limit = validated_data.get('limit', 5)
        min_score_threshold = validated_data.get('min_score_threshold', 6.0)
        
        # Check cache
        cache_key = generate_cache_key(
            "ml_alternatives", 
            request.user.id, 
            {'product_code': product_code, 'limit': limit, 'threshold': min_score_threshold}
        )
        cached_result = cache.get(cache_key)
        if cached_result:
            return Response(cached_result, status=status.HTTP_200_OK)
        
        # Get user profile for ML analysis
        user_profile = get_user_profile_data(request.user)
        
        # Get ML-based alternatives
        alternatives_result = ml_recommendation_service.get_product_alternatives(
            user_profile=user_profile,
            target_product_code=product_code,
            limit=limit,
            min_score_threshold=min_score_threshold
        )
        
        if not alternatives_result:
            return Response({
                'error': 'Unable to generate alternatives for this product'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Serialize alternatives
        alternatives_data = []
        for alt in alternatives_result['alternatives']:
            product_data = alt['product']
            # Add ML scores to product data
            for key in ['final_score', 'ml_score', 'target_score', 'score_improvement', 
                       'similarity_bonus', 'improvement_bonus', 'reason', 'category_match']:
                setattr(product_data, key, alt[key])
            
            alternatives_data.append(product_data)
        
        # Use response serializer
        response_data = {
            'alternatives': ProductRecommendationSerializer(alternatives_data, many=True).data,
            'target_product': alternatives_result['target_product'],
            'recommendation_stats': alternatives_result['recommendation_stats']
        }
        
        # Cache for 5 minutes
        cache.set(cache_key, response_data, 300)
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Alternatives recommendation error: {str(e)}")
        return Response({
            'error': f'Failed to get alternatives: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
"""
