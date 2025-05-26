from django.shortcuts import render
from django.http import JsonResponse
from api.models import User, Profile
from api.serializer import MyTokenObtainPairSerializer, RegisterSerializer, ProfileSerializer
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from django.core.cache import cache
import requests
from django.http import JsonResponse
from aimodels.product_analysis import ProductAnalyzer
import hashlib
import json


class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer


# Get All Routes
@api_view(['GET'])
def getRoutes(request):
    routes = [
        '/api/token/',
        '/api/register/',
        '/api/token/refresh/',
        '/api/profile/',
        '/api/analyze-product/',
        '/api/product-warnings/',
        '/api/search-product/',
    ]
    return Response(routes)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getUserProfile(request):
    user = request.user
    try:
        profile = Profile.objects.get(user=user)
        serializer = ProfileSerializer(profile)
        return Response(serializer.data)
    except Profile.DoesNotExist:
        return Response({'error': 'Profile not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def testEndPoint(request):
    if request.method == 'GET':
        data = f"Congratulation {request.user}, your API just responded to GET request"
        return Response({'response': data}, status=status.HTTP_200_OK)
    elif request.method == 'POST':
        text = "Hello buddy"
        data = f'Congratulation your API just responded to POST request with text: {text}'
        return Response({'response': data}, status=status.HTTP_200_OK)
    return Response({}, status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    profile = request.user.profile
    serializer = ProfileSerializer(profile, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=400)


def get_user_profile_data(user):
    """Kullanıcı profil verisini normalize et"""
    try:
        user_profile = Profile.objects.get(user=user)
        return {
            'allergies': user_profile.allergies or [],
            'dietary_preferences': user_profile.dietary_preferences or [],
            'health_conditions': user_profile.medical_conditions or [],
            'age': getattr(user_profile, 'age', 30),
            'gender': getattr(user_profile, 'gender', 'other'),
            'activity_level': getattr(user_profile, 'activity_level', 'moderate'),
            'health_goals': getattr(user_profile, 'health_goals', [])
        }
    except Profile.DoesNotExist:
        return {
            'allergies': [],
            'dietary_preferences': [],
            'health_conditions': [],
            'age': 30,
            'gender': 'other',
            'activity_level': 'moderate',
            'health_goals': []
        }


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analyze_product_complete(request):
    """
    Ürünü kapsamlı analiz et - uyarılar, öneriler, sağlık skoru
    """
    try:
        data = request.data
        product_data = data.get('product_data')
        
        if not product_data:
            return Response({
                'error': 'Ürün verisi gerekli'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Kullanıcı profilini al
        user_profile_data = get_user_profile_data(request.user)
        
        # Cache key oluştur
        cache_key = f"product_analysis_{request.user.id}_{hashlib.md5(json.dumps(product_data, sort_keys=True).encode()).hexdigest()}"
        
        # Cache'den kontrol et
        cached_result = cache.get(cache_key)
        if cached_result:
            return Response(cached_result, status=status.HTTP_200_OK)
        
        analyzer = ProductAnalyzer()
        analysis_result = analyzer.analyze_product_complete(product_data, user_profile_data)
        
        # Sonucu cache'le (5 dakika)
        cache.set(cache_key, analysis_result, 300)
        
        return Response(analysis_result, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Analiz sırasında hata oluştu: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_product_warnings_only(request):
    """
    Sadece uyarıları getir (daha hızlı)
    """
    try:
        data = request.data
        product_data = data.get('product_data')
        
        if not product_data:
            return Response({
                'error': 'Ürün verisi gerekli'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Kullanıcı profilini al
        user_profile_data = get_user_profile_data(request.user)
        
        # Cache key oluştur (sadece uyarılar için)
        cache_key = f"product_warnings_{request.user.id}_{hashlib.md5(json.dumps(product_data, sort_keys=True).encode()).hexdigest()}"
        
        # Cache'den kontrol et
        cached_result = cache.get(cache_key)
        if cached_result:
            return Response(cached_result, status=status.HTTP_200_OK)
        
        analyzer = ProductAnalyzer()
        warnings_result = analyzer.analyze_warnings_only(product_data, user_profile_data)
        
        # Sonucu cache'le (2 dakika)
        cache.set(cache_key, warnings_result, 120)
        
        return Response(warnings_result, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Uyarı analizi sırasında hata oluştu: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def search_product(request):
    """
    OpenFoodFacts'ten ürün arama ve filtreleme
    """
    query = request.GET.get('query', '')

    if not query:
        return JsonResponse({'error': 'No query parameter provided'}, status=400)

    # OpenFoodFacts API'den veri çek
    url = f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={query}&search_simple=1&action=process&json=1"
    response = requests.get(url)

    if response.status_code != 200:
        return JsonResponse({'error': 'Failed to fetch data from OpenFoodFacts'}, status=500)

    data = response.json()
    products = data.get('products', [])

    # ProductAnalyzer'dan filtre metodlarını kullan
    analyzer = ProductAnalyzer()
    filters = analyzer.parse_filter_params(request.GET.dict())
    filtered_products = analyzer.apply_filters(products, filters) if filters else products

    # Eğer kullanıcı login olmuşsa analiz ekle
    if request.user.is_authenticated:
        try:
            user_profile_data = get_user_profile_data(request.user)
            analyzed_products = []
            
            # İlk 10 ürün için hızlı analiz yap (performans için)
            for product in filtered_products[:10]:
                try:
                    # Cache key oluştur
                    cache_key = f"quick_analysis_{request.user.id}_{product.get('id', 'unknown')}"
                    cached_analysis = cache.get(cache_key)
                    
                    if cached_analysis:
                        product['analysis'] = cached_analysis
                    else:
                        # Hızlı analiz için sadece uyarıları al
                        analysis = analyzer.analyze_warnings_only(product, user_profile_data)
                        quick_analysis = {
                            'warnings': analysis.get('warnings', [])[:3],  # İlk 3 uyarı
                            'critical_issues': analysis.get('critical_issues', 0),
                            'has_alerts': len(analysis.get('warnings', [])) > 0
                        }
                        cache.set(cache_key, quick_analysis, 300)
                        product['analysis'] = quick_analysis
                        
                except Exception as e:
                    product['analysis'] = {'error': f'Analiz hatası: {str(e)}'}
                
                analyzed_products.append(product)
            
            # Kalan ürünleri analiz olmadan ekle
            analyzed_products.extend(filtered_products[10:])
            
            return JsonResponse({'products': analyzed_products}, safe=False)
            
        except Exception as e:
            return JsonResponse({
                'products': filtered_products,
                'analysis_error': f'Analiz hatası: {str(e)}'
            }, safe=False)
    return JsonResponse({'products': filtered_products}, safe=False)