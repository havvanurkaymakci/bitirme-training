# api/urls/product_urls.py

from django.urls import path
from api.views import product_views

urlpatterns = [
    # Ana arama endpoint'i - frontend ile uyumlu
    path('product-search/', product_views.product_search, name='product_search'),
    path('search/', product_views.product_search, name='product_search_alt'),  # alternatif
    
    # Ürün detay endpoint'leri
    path('detail/<str:product_code>/', product_views.get_product_detail, name='product_detail'),
    path('<str:product_code>/', product_views.get_product_detail, name='product_detail_alt'),
    
    # Analiz endpoint'leri (POST)
    path('analyze/', product_views.analyze_product_complete, name='analyze_product_complete'),
    path('compare/', product_views.compare_products, name='compare_products'),
    
    # ML tabanlı endpoint'ler (GET) - EKLENMİŞ
    path('personalized-score/', product_views.get_personalized_product_score, name='personalized_score'),
    path('ml-recommendations/', product_views.get_ml_recommendations, name='ml_recommendations'),
    path('warnings-only/', product_views.get_product_warnings_only, name='product_warnings_only'),
]