# api/urls/product_urls.py
from django.urls import path
from api.views import product_views

urlpatterns = [
    # Mevcut URL'ler
    path('search/', product_views.product_search, name='product_search'),
    path('analyze/', product_views.analyze_product_complete, name='analyze_product_complete'),
    path('warnings/', product_views.get_product_warnings_only, name='product_warnings'),
    
    # Ek endpoint'ler
    path('<str:product_code>/', product_views.get_product_detail, name='product_detail'),
    path('compare/', product_views.compare_products, name='compare_products'),
    path('<str:product_code>/recommendations/', product_views.get_recommendations, name='product_recommendations'),
    path('bulk/create/', product_views.bulk_create_products, name='bulk_create_products'),
    path('stats/', product_views.get_product_stats, name='product_stats'),
]