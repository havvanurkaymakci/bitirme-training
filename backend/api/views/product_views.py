# api/views/product_views.py

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, Avg, Count
from django.shortcuts import get_object_or_404
from django.core.cache import cache
import logging

from api.models.product_features import ProductFeatures, ProductSimilarity
from api.serializers.product_serializer import (
    ProductFeaturesSerializer,
    ProductFeaturesListSerializer,
    ProductFeaturesDetailSerializer,
    ProductSimilaritySerializer,
    ProductRecommendationSerializer,
    ProductSearchSerializer,
    ProductComparisonSerializer,
    ProductAnalysisSerializer,
    BulkProductCreateSerializer,
    ProductStatsSerializer
)

logger = logging.getLogger(__name__)


class ProductPagination(PageNumberPagination):
    """Ürün listesi için özel pagination"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def product_search(request):
    """
    Ürün arama endpoint'i
    GET: Tüm ürünleri listele
    POST: Filtreleme parametreleri ile arama yap
    """
    try:
        if request.method == 'GET':
            # Basit listeleme
            queryset = ProductFeatures.objects.filter(is_valid_for_analysis=True)
            
            # URL parametrelerinden basit filtreler
            category = request.GET.get('category')
            brand = request.GET.get('brand')
            query = request.GET.get('q')
            
            if category:
                queryset = queryset.filter(main_category__icontains=category)
            if brand:
                queryset = queryset.filter(main_brand__icontains=brand)
            if query:
                queryset = queryset.filter(
                    Q(product_name__icontains=query) |
                    Q(main_category__icontains=query) |
                    Q(main_brand__icontains=query)
                )
            
            # Pagination
            paginator = ProductPagination()
            page = paginator.paginate_queryset(queryset, request)
            
            serializer = ProductFeaturesListSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        elif request.method == 'POST':
            # Gelişmiş arama
            serializer = ProductSearchSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            search_params = serializer.validated_data
            queryset = ProductFeatures.objects.filter(is_valid_for_analysis=True)
            
            # Metin arama
            if search_params.get('query'):
                query = search_params['query']
                queryset = queryset.filter(
                    Q(product_name__icontains=query) |
                    Q(main_category__icontains=query) |
                    Q(main_brand__icontains=query) |
                    Q(ingredients_text__icontains=query)
                )
            
            # Kategori filtresi
            if search_params.get('category'):
                queryset = queryset.filter(main_category__icontains=search_params['category'])
            
            # Marka filtresi
            if search_params.get('brand'):
                queryset = queryset.filter(main_brand__icontains=search_params['brand'])
            
            # Beslenme skoru aralığı
            if search_params.get('min_nutrition_score'):
                queryset = queryset.filter(nutrition_quality_score__gte=search_params['min_nutrition_score'])
            if search_params.get('max_nutrition_score'):
                queryset = queryset.filter(nutrition_quality_score__lte=search_params['max_nutrition_score'])
            
            # İşlenmişlik düzeyi
            if search_params.get('processing_level'):
                queryset = queryset.filter(processing_level=search_params['processing_level'])
            
            # Alerjen filtreleme
            if search_params.get('allergens_to_avoid'):
                for allergen in search_params['allergens_to_avoid']:
                    queryset = queryset.exclude(allergen_vector__contains={f'contains_{allergen}': 1})
            
            # Sağlık göstergeleri
            if search_params.get('health_indicators'):
                for indicator in search_params['health_indicators']:
                    queryset = queryset.filter(health_indicators__contains={indicator: 1})
            
            # Nutriscore filtreleme
            if search_params.get('nutriscore_grades'):
                grades_filter = Q()
                for grade in search_params['nutriscore_grades']:
                    grades_filter |= Q(nutriscore_data__nutriscore_grade=grade)
                queryset = queryset.filter(grades_filter)
            
            # Sıralama
            queryset = queryset.order_by('-nutrition_quality_score', '-health_score')
            
            # Pagination
            paginator = ProductPagination()
            page = paginator.paginate_queryset(queryset, request)
            
            serializer = ProductFeaturesListSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
    
    except Exception as e:
        logger.error(f"Product search error: {str(e)}")
        return Response(
            {'error': 'Arama sırasında bir hata oluştu.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analyze_product_complete(request):
    """
    Ürün analizi - kapsamlı analiz ve öneriler
    """
    try:
        product_code = request.data.get('product_code')
        if not product_code:
            return Response(
                {'error': 'product_code gerekli.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Cache kontrolü
        cache_key = f'product_analysis_{product_code}'
        cached_result = cache.get(cache_key)
        if cached_result:
            return Response(cached_result)
        
        product = get_object_or_404(ProductFeatures, product_code=product_code)
        
        # Analiz sonuçları
        analysis_result = {
            'product': ProductFeaturesDetailSerializer(product).data,
            'health_warnings': [],
            'dietary_warnings': [],
            'allergy_warnings': [],
            'recommendations': [],
            'nutritional_analysis': {},
            'overall_rating': 0.0,
            'rating_explanation': ''
        }
        
        # Sağlık uyarıları
        if product.is_high_sugar():
            analysis_result['health_warnings'].append('Yüksek şeker içeriği')
        if product.is_high_salt():
            analysis_result['health_warnings'].append('Yüksek tuz içeriği')
        if product.is_high_fat():
            analysis_result['health_warnings'].append('Yüksek yağ içeriği')
        if product.is_high_calorie():
            analysis_result['health_warnings'].append('Yüksek kalori içeriği')
        if product.has_risky_additives():
            analysis_result['health_warnings'].append('Riskli katkı maddeleri içeriyor')
        
        # İşlenmişlik uyarısı
        if product.processing_level >= 4:
            analysis_result['dietary_warnings'].append('Ultra işlenmiş gıda')
        elif product.processing_level >= 3:
            analysis_result['dietary_warnings'].append('Yoğun işlenmiş gıda')
        
        # Alerjen uyarıları
        allergens = product.get_all_allergens()
        if allergens:
            analysis_result['allergy_warnings'] = [
                f'{allergen.title()} alerjeni içeriyor' for allergen in allergens
            ]
        
        # Besin analizi
        analysis_result['nutritional_analysis'] = {
            'energy_kcal': product.get_energy_kcal(),
            'protein': product.get_protein(),
            'fat': product.get_fat(),
            'sugar': product.get_sugar(),
            'salt': product.get_salt(),
            'fiber': product.get_fiber(),
            'nutriscore_grade': product.get_nutriscore_grade(),
            'additives_count': product.get_additives_count(),
            'macro_ratios': product.macro_ratios
        }
        
        # Genel değerlendirme
        rating = product.nutrition_quality_score
        analysis_result['overall_rating'] = rating
        
        if rating >= 8:
            analysis_result['rating_explanation'] = 'Mükemmel beslenme profili'
        elif rating >= 6:
            analysis_result['rating_explanation'] = 'İyi beslenme profili'
        elif rating >= 4:
            analysis_result['rating_explanation'] = 'Orta düzey beslenme profili'
        else:
            analysis_result['rating_explanation'] = 'Zayıf beslenme profili'
        
        # Benzer ürün önerileri
        recommendations = get_product_recommendations(product, limit=5)
        analysis_result['recommendations'] = ProductRecommendationSerializer(
            recommendations, many=True
        ).data
        
        # Cache'e kaydet (5 dakika)
        cache.set(cache_key, analysis_result, 300)
        
        return Response(analysis_result)
    
    except Exception as e:
        logger.error(f"Product analysis error: {str(e)}")
        return Response(
            {'error': 'Analiz sırasında bir hata oluştu.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_product_warnings_only(request):
    """
    Sadece ürün uyarılarını döndürür (hızlı kontrol için)
    """
    try:
        product_code = request.data.get('product_code')
        if not product_code:
            return Response(
                {'error': 'product_code gerekli.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        product = get_object_or_404(ProductFeatures, product_code=product_code)
        
        warnings = {
            'product_code': product_code,
            'product_name': product.product_name,
            'health_warnings': [],
            'allergy_warnings': [],
            'processing_warning': None,
            'warning_count': 0
        }
        
        # Sağlık uyarıları
        if product.is_high_sugar():
            warnings['health_warnings'].append('high_sugar')
        if product.is_high_salt():
            warnings['health_warnings'].append('high_salt')
        if product.is_high_fat():
            warnings['health_warnings'].append('high_fat')
        if product.has_risky_additives():
            warnings['health_warnings'].append('risky_additives')
        
        # Alerjen uyarıları
        warnings['allergy_warnings'] = product.get_all_allergens()
        
        # İşlenmişlik uyarısı
        if product.processing_level >= 4:
            warnings['processing_warning'] = 'ultra_processed'
        elif product.processing_level >= 3:
            warnings['processing_warning'] = 'highly_processed'
        
        # Toplam uyarı sayısı
        warnings['warning_count'] = (
            len(warnings['health_warnings']) + 
            len(warnings['allergy_warnings']) + 
            (1 if warnings['processing_warning'] else 0)
        )
        
        return Response(warnings)
    
    except Exception as e:
        logger.error(f"Product warnings error: {str(e)}")
        return Response(
            {'error': 'Uyarılar alınırken bir hata oluştu.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_product_detail(request, product_code):
    """
    Ürün detay bilgilerini döndürür
    """
    try:
        product = get_object_or_404(ProductFeatures, product_code=product_code)
        serializer = ProductFeaturesDetailSerializer(product)
        return Response(serializer.data)
    
    except Exception as e:
        logger.error(f"Product detail error: {str(e)}")
        return Response(
            {'error': 'Ürün detayları alınırken bir hata oluştu.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def compare_products(request):
    """
    Ürün karşılaştırması
    """
    try:
        serializer = ProductComparisonSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        product_codes = serializer.validated_data['product_codes']
        comparison_fields = serializer.validated_data.get('comparison_fields', [
            'nutrition_quality_score', 'health_score', 'processing_level'
        ])
        
        products = ProductFeatures.objects.filter(
            product_code__in=product_codes,
            is_valid_for_analysis=True
        )
        
        if len(products) != len(product_codes):
            return Response(
                {'error': 'Bazı ürünler bulunamadı.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        comparison_result = {
            'products': ProductFeaturesDetailSerializer(products, many=True).data,
            'comparison': {},
            'winner': None,
            'summary': {}
        }
        
        # Her alan için karşılaştırma
        for field in comparison_fields:
            field_values = []
            for product in products:
                if hasattr(product, field):
                    value = getattr(product, field)
                    field_values.append({
                        'product_code': product.product_code,
                        'product_name': product.product_name,
                        'value': value
                    })
            
            # En iyi değeri bul
            if field in ['nutrition_quality_score', 'health_score']:
                best = max(field_values, key=lambda x: x['value'] if x['value'] else 0)
            elif field == 'processing_level':
                best = min(field_values, key=lambda x: x['value'] if x['value'] else 5)
            else:
                best = max(field_values, key=lambda x: x['value'] if x['value'] else 0)
            
            comparison_result['comparison'][field] = {
                'values': field_values,
                'best_product': best
            }
        
        # Genel galibi belirle (nutrition_quality_score'a göre)
        best_nutrition = max(products, key=lambda x: x.nutrition_quality_score)
        comparison_result['winner'] = {
            'product_code': best_nutrition.product_code,
            'product_name': best_nutrition.product_name,
            'reason': 'En yüksek beslenme kalite skoru'
        }
        
        return Response(comparison_result)
    
    except Exception as e:
        logger.error(f"Product comparison error: {str(e)}")
        return Response(
            {'error': 'Karşılaştırma sırasında bir hata oluştu.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_recommendations(request, product_code):
    """
    Belirli bir ürün için öneriler
    """
    try:
        product = get_object_or_404(ProductFeatures, product_code=product_code)
        limit = int(request.GET.get('limit', 10))
        
        recommendations = get_product_recommendations(product, limit=limit)
        serializer = ProductRecommendationSerializer(recommendations, many=True)
        
        return Response({
            'base_product': {
                'code': product.product_code,
                'name': product.product_name
            },
            'recommendations': serializer.data
        })
    
    except Exception as e:
        logger.error(f"Recommendations error: {str(e)}")
        return Response(
            {'error': 'Öneriler alınırken bir hata oluştu.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_create_products(request):
    """
    Toplu ürün ekleme
    """
    try:
        serializer = BulkProductCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        result = serializer.save()
        return Response({
            'message': f'{result["count"]} ürün başarıyla eklendi.',
            'created_count': result['count']
        }, status=status.HTTP_201_CREATED)
    
    except Exception as e:
        logger.error(f"Bulk create error: {str(e)}")
        return Response(
            {'error': 'Toplu ekleme sırasında bir hata oluştu.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_product_stats(request):
    """
    Genel ürün istatistikleri
    """
    try:
        cache_key = 'product_stats'
        cached_stats = cache.get(cache_key)
        if cached_stats:
            return Response(cached_stats)
        
        queryset = ProductFeatures.objects.filter(is_valid_for_analysis=True)
        
        stats = {
            'total_products': queryset.count(),
            'categories': dict(queryset.values_list('main_category').annotate(Count('main_category'))),
            'brands': dict(queryset.exclude(main_brand__isnull=True).values_list('main_brand').annotate(Count('main_brand'))[:20]),
            'processing_levels': dict(queryset.values_list('processing_level').annotate(Count('processing_level'))),
            'nutriscore_distribution': {},
            'average_nutrition_score': queryset.aggregate(Avg('nutrition_quality_score'))['nutrition_quality_score__avg'] or 0,
            'average_health_score': queryset.aggregate(Avg('health_score'))['health_score__avg'] or 0
        }
        
        # Nutriscore dağılımı
        nutriscore_counts = {}
        for product in queryset.exclude(nutriscore_data={}):
            grade = product.get_nutriscore_grade()
            if grade:
                nutriscore_counts[grade] = nutriscore_counts.get(grade, 0) + 1
        stats['nutriscore_distribution'] = nutriscore_counts
        
        # Cache'e kaydet (30 dakika)
        cache.set(cache_key, stats, 1800)
        
        return Response(stats)
    
    except Exception as e:
        logger.error(f"Product stats error: {str(e)}")
        return Response(
            {'error': 'İstatistikler alınırken bir hata oluştu.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Yardımcı fonksiyonlar

def get_product_recommendations(product, limit=5):
    """
    Ürün için öneriler getirir
    """
    try:
        # Önce benzerlik tablosundan bak
        similarities = ProductSimilarity.objects.filter(
            Q(product_1=product) | Q(product_2=product)
        ).order_by('-overall_similarity')[:limit]
        
        recommendations = []
        for sim in similarities:
            recommended_product = sim.product_2 if sim.product_1 == product else sim.product_1
            
            # Serializer için ek alanlar ekle
            recommended_product.similarity_score = sim.overall_similarity
            recommended_product.recommendation_reason = get_recommendation_reason(product, recommended_product, sim)
            recommendations.append(recommended_product)
        
        # Benzerlik tablosu yetersizse kategori bazlı öneriler
        if len(recommendations) < limit:
            category_products = ProductFeatures.objects.filter(
                main_category=product.main_category,
                is_valid_for_analysis=True
            ).exclude(id=product.id).order_by('-nutrition_quality_score')[:limit - len(recommendations)]
            
            for cat_product in category_products:
                cat_product.similarity_score = 0.8  # Varsayılan benzerlik
                cat_product.recommendation_reason = f"Aynı kategori ({product.main_category})"
                recommendations.append(cat_product)
        
        return recommendations[:limit]
    
    except Exception as e:
        logger.error(f"Recommendations error: {str(e)}")
        return []


def get_recommendation_reason(base_product, recommended_product, similarity):
    """
    Öneri sebebini belirler
    """
    reasons = []
    
    if similarity.nutritional_similarity > 0.8:
        reasons.append("Benzer besin değerleri")
    
    if similarity.category_similarity > 0.9:
        reasons.append("Aynı kategori")
    
    if recommended_product.nutrition_quality_score > base_product.nutrition_quality_score:
        reasons.append("Daha iyi beslenme skoru")
    
    if recommended_product.processing_level < base_product.processing_level:
        reasons.append("Daha az işlenmiş")
    
    return " • ".join(reasons) if reasons else "Genel benzerlik"