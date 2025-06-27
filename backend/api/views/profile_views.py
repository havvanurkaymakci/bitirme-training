
from django.shortcuts import render
from django.http import JsonResponse
from api.models.user_profile import User, Profile
from api.serializers.profile_serializer import MyTokenObtainPairSerializer, RegisterSerializer, ProfileSerializer
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import logging

logger = logging.getLogger(__name__)


class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


@method_decorator(csrf_exempt, name='dispatch')
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
        '/api/test/',
        '/api/profile/update/',
    ]
    return Response(routes)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getUserProfile(request):
    """Kullanıcı profil bilgilerini getir"""
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
    """Test endpoint - hem GET hem POST isteklerini destekler"""
    if request.method == 'GET':
        data = f"Congratulation {request.user}, your API just responded to GET request"
        return Response({'response': data}, status=status.HTTP_200_OK)
    elif request.method == 'POST':
        text = request.data.get('text', 'Hello buddy')
        data = f'Congratulation your API just responded to POST request with text: {text}'
        return Response({'response': data}, status=status.HTTP_200_OK)
    return Response({'error': 'Method not allowed'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """Kullanıcı profil bilgilerini güncelle"""
    try:
        # Kullanıcının profili var mı kontrol et
        try:
            profile = request.user.profile
        except Profile.DoesNotExist:
            # Profil yoksa oluştur
            profile = Profile.objects.create(user=request.user)
        
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        logger.error(f"Profil güncelleme hatası: {str(e)}")
        return Response({
            'error': f'Profil güncellenirken hata oluştu: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@csrf_exempt
def create_profile(request):
    """Yeni kullanıcı profili oluştur"""
    try:
        # Kullanıcının zaten profili var mı kontrol et
        if hasattr(request.user, 'profile'):
            return Response({
                'error': 'Kullanıcının zaten profili var'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Yeni profil oluştur
        serializer = ProfileSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        logger.error(f"Profil oluşturma hatası: {str(e)}")
        return Response({
            'error': f'Profil oluşturulurken hata oluştu: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@csrf_exempt
def delete_profile(request):
    """Kullanıcı profilini sil"""
    try:
        profile = request.user.profile
        profile.delete()
        return Response({
            'message': 'Profil başarıyla silindi'
        }, status=status.HTTP_200_OK)
        
    except Profile.DoesNotExist:
        return Response({
            'error': 'Profil bulunamadı'
        }, status=status.HTTP_404_NOT_FOUND)
        
    except Exception as e:
        logger.error(f"Profil silme hatası: {str(e)}")
        return Response({
            'error': f'Profil silinirken hata oluştu: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def get_user_profile_data(user):
    """Kullanıcı profil verisini normalize et - diğer uygulamalar için helper"""
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@csrf_exempt
def get_profile_stats(request):
    """Profil istatistikleri - opsiyonel özellik"""
    try:
        profile = request.user.profile
        
        stats = {
            'profile_completion': 0,
            'last_updated': profile.updated_at if hasattr(profile, 'updated_at') else None,
            'has_allergies': bool(profile.allergies),
            'has_dietary_preferences': bool(profile.dietary_preferences),
            'has_health_conditions': bool(profile.medical_conditions),
            'has_age': bool(getattr(profile, 'age', None)),
            'has_gender': bool(getattr(profile, 'gender', None)),
        }
        
        # Profil tamamlanma yüzdesi hesapla
        total_fields = 6
        completed_fields = sum([
            stats['has_allergies'],
            stats['has_dietary_preferences'], 
            stats['has_health_conditions'],
            stats['has_age'],
            stats['has_gender'],
            bool(getattr(profile, 'activity_level', None))
        ])
        
        stats['profile_completion'] = int((completed_fields / total_fields) * 100)
        
        return Response(stats, status=status.HTTP_200_OK)
        
    except Profile.DoesNotExist:
        return Response({
            'error': 'Profil bulunamadı'
        }, status=status.HTTP_404_NOT_FOUND)
        
    except Exception as e:
        logger.error(f"Profil istatistikleri hatası: {str(e)}")
        return Response({
            'error': f'İstatistikler alınırken hata oluştu: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
@csrf_exempt
def update_profile_field(request, field_name):
    """Profil alanını tek tek güncelle"""
    try:
        profile = request.user.profile
        
        # İzin verilen alanları kontrol et
        allowed_fields = [
            'allergies', 'dietary_preferences', 'medical_conditions',
            'age', 'gender', 'activity_level', 'health_goals'
        ]
        
        if field_name not in allowed_fields:
            return Response({
                'error': f'Geçersiz alan: {field_name}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Yeni değeri al
        new_value = request.data.get('value')
        if new_value is None:
            return Response({
                'error': 'Değer gerekli'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Profili güncelle
        setattr(profile, field_name, new_value)
        profile.save()
        
        return Response({
            'message': f'{field_name} başarıyla güncellendi',
            'field': field_name,
            'new_value': new_value
        }, status=status.HTTP_200_OK)
        
    except Profile.DoesNotExist:
        return Response({
            'error': 'Profil bulunamadı'
        }, status=status.HTTP_404_NOT_FOUND)
        
    except Exception as e:
        logger.error(f"Alan güncelleme hatası: {str(e)}")
        return Response({
            'error': f'Alan güncellenirken hata oluştu: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)