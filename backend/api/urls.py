from django.urls import path
from . import views

from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

urlpatterns = [
    path('token/', views.MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register/', views.RegisterView.as_view(), name='auth_register'),
    path('profile/', views.getUserProfile, name='user_profile'), 
    path('profile/edit/', views.update_profile, name='edit_profile'),    path('test/', views.testEndPoint, name='test'),
    path('product-search/', views.search_product, name='product_search'),
    path('', views.getRoutes),
]