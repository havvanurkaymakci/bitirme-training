# api/urls/auth_urls.py
from django.urls import path
from api.views.profile_views import (
    MyTokenObtainPairView, 
    RegisterView, 
    getRoutes, 
    getUserProfile, 
    testEndPoint, 
    update_profile,
)
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('', getRoutes),
    path('token/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register/', RegisterView.as_view(), name='auth_register'),
    path('test/', testEndPoint, name='test'),
    path('profile/', getUserProfile, name='get_user_profile'),
    path('profile/update/', update_profile, name='update_profile'),
]
