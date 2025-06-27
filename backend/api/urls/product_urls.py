# api/urls/product_urls.py

from django.urls import path
from api.views import product_views

urlpatterns = [
    # Ana endpoint'ler
    path('product-search/', product_views.product_search, name='product_search'),
     # GET endpoints
    path('personalized-score/', product_views.get_personalized_product_score, name='personalized_score'),  # GET
    path('ml-recommendations/', product_views.get_ml_recommendations, name='ml_recommendations'),  # GET
    path('product-warnings-only/', product_views.get_product_warnings_only, name='product_warnings_only'),  # GET
    
    # POST endpoints  
    path('analyze/', product_views.analyze_product_complete, name='analyze_product_complete'),  # POST
    path('personalized-warnings/', product_views.get_personalized_warnings, name='personalized_warnings'),  # POST
    path('compare/', product_views.compare_products, name='compare_products'),  # POST
    path('health-analysis/<str:product_code>/', product_views.get_health_analysis, name='health_analysis'),
    
    # Detay ve yönetim endpoint'leri
    path('product-detail/<str:product_code>/', product_views.get_product_detail, name='product_detail_react'),
    path('<str:product_code>/', product_views.get_product_detail, name='product_detail'),
    # path('bulk/create/', product_views.bulk_create_products, name='bulk_create_products'),
    # path('stats/', product_views.get_product_stats, name='product_stats'),
]

# React component uyumluluğu için ana urls.py'ye eklenmesi gereken:
# path('api/ml-recommendations/', include('api.urls.direct_ml_urls')),

