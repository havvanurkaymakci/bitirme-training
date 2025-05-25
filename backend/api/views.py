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
import requests
from django.http import JsonResponse
from aimodels.recommendation_engine import analyze_products_for_user 
from aimodels.filters import apply_filters 
 

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
        '/api/profile/',  # Yeni profil endpoint'i
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



@api_view(['GET'])
@permission_classes([AllowAny])
def search_product(request):
    query = request.GET.get('query', '')

    if not query:
        return JsonResponse({'error': 'No query parameter provided'}, status=400)

    url = f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={query}&search_simple=1&action=process&json=1"
    response = requests.get(url)

    if response.status_code != 200:
        return JsonResponse({'error': 'Failed to fetch data from OpenFoodFacts'}, status=500)

    data = response.json()
    products = data.get('products', [])

    # URL'den filtre parametrelerini al ve dictionary olarak hazırla
    def parse_filter_params(request):
        filter_keys = [
            'max_energy_kcal', 'max_sugar', 'max_fat', 'max_saturated_fat',
            'max_salt', 'max_sodium', 'min_fiber', 'min_proteins', 'max_proteins',
            'is_vegan', 'is_vegetarian', 'nutriscore_grade', 'nova_group',
        ]
        filters = {}

        for key in filter_keys:
            value = request.GET.get(key)
            if value is not None:
                if key in ['is_vegan', 'is_vegetarian']:
                    filters[key] = value.lower() == 'true'
                elif key in ['nutriscore_grade', 'nova_group']:
                    if value:
                        filters[key] = value.upper().split(',') if ',' in value else [value.upper()]
                else:
                    try:
                        filters[key] = float(value)
                    except ValueError:
                        continue

        # include_ingredients ve exclude_ingredients virgülle ayrılabilir
        include = request.GET.get('include_ingredients', '')
        exclude = request.GET.get('exclude_ingredients', '')
        if include:
            filters['include_ingredients'] = [item.strip() for item in include.split(',')]
        if exclude:
            filters['exclude_ingredients'] = [item.strip() for item in exclude.split(',')]

        return filters

    filters = parse_filter_params(request)
    filtered_products = apply_filters(products, filters) if filters else products

    # Eğer kullanıcı login olmuşsa öneri/filtre/uyarı çalıştır
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            personalized_data = analyze_products_for_user(profile, {'products': filtered_products})
            return JsonResponse(personalized_data, safe=False)
        except Profile.DoesNotExist:
            return JsonResponse({'error': 'User profile not found'}, status=404)

    return JsonResponse({'products': filtered_products}, safe=False)
