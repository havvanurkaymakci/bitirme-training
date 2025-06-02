from django.urls import include, path

urlpatterns = [
    path('products/', include('api.urls.product_urls')),
    path('auth/', include('api.urls.auth_urls')),
]
