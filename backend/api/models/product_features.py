# backend/models/product_features.py

from django.db import models
import json


class ProductFeatures(models.Model):
    """
    OpenFoodFacts verilerinden çıkarılan ürün özelliklerini saklar
    """
    # Ana ürün bilgileri
    product_code = models.CharField(max_length=50, unique=True, db_index=True)
    product_name = models.CharField(max_length=500)
    main_category = models.CharField(max_length=200, db_index=True)
    main_brand = models.CharField(max_length=200, null=True, blank=True)
    main_country = models.CharField(max_length=100, null=True, blank=True)
    
    # Besin değerleri (100g başına) - JSON formatında saklanıyor
    nutrition_vector = models.JSONField(default=dict, help_text="100g başına besin değerleri")
    
    # Alerjen bilgileri - Binary vektör formatında
    allergen_vector = models.JSONField(default=dict, help_text="Alerjen varlık bilgileri (binary)")
    
    # Katkı madde bilgileri
    additives_info = models.JSONField(default=dict, help_text="Katkı madde bilgileri ve sayıları")
    
    # Nutriscore verileri
    nutriscore_data = models.JSONField(default=dict, help_text="Nutriscore grade ve numeric değerleri")
    
    # İşlenmişlik düzeyi (1-4: minimal -> ultra-processed)
    processing_level = models.IntegerField(default=1, choices=[
        (1, 'Minimal İşlenmiş'),
        (2, 'İşlenmiş Malzemeler'),
        (3, 'İşlenmiş Gıdalar'),
        (4, 'Ultra İşlenmiş Gıdalar')
    ])
    
    # Sağlık skorları ve göstergeleri
    health_indicators = models.JSONField(default=dict, help_text="Sağlık göstergeleri (high_sugar, high_salt, vb.)")
    nutrition_quality_score = models.FloatField(default=5.0, help_text="0-10 arası beslenme kalite skoru")
    health_score = models.FloatField(default=0.0, help_text="Composite health score")
    
    # Makro besin oranları
    macro_ratios = models.JSONField(default=dict, help_text="Makro besin oranları")
    
    # Text özellikler
    ingredients_text = models.TextField(blank=True, help_text="İçerik listesi (temizlenmiş)")
    ingredients_text_length = models.IntegerField(default=0)
    ingredients_word_count = models.IntegerField(default=0)
    
    # Kalite kontrol
    data_completeness_score = models.FloatField(default=0.0, help_text="Veri tamlık skoru (0-1)")
    is_valid_for_analysis = models.BooleanField(default=True, help_text="Analiz için geçerli mi?")
    
    # Zaman damgaları
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'product_features'
        indexes = [
            models.Index(fields=['main_category']),
            models.Index(fields=['processing_level']),
            models.Index(fields=['nutrition_quality_score']),
            models.Index(fields=['is_valid_for_analysis']),
        ]
        
    def __str__(self):
        return f"{self.product_name} ({self.product_code})"
    
    # Besin değeri getter metodları
    def get_energy_kcal(self):
        return self.nutrition_vector.get('energy_kcal_100g', 0)
    
    def get_fat(self):
        return self.nutrition_vector.get('fat_100g', 0)
    
    def get_sugar(self):
        return self.nutrition_vector.get('sugars_100g', 0)
    
    def get_salt(self):
        return self.nutrition_vector.get('salt_100g', 0)
    
    def get_protein(self):
        return self.nutrition_vector.get('proteins_100g', 0)
    
    def get_fiber(self):
        return self.nutrition_vector.get('fiber_100g', 0)
    
    # Alerjen kontrol metodları
    def contains_allergen(self, allergen_name):
        """Belirli bir alerjen içeriyor mu?"""
        return self.allergen_vector.get(f'contains_{allergen_name}', 0) == 1
    
    def get_all_allergens(self):
        """Tüm alerjenleri listele"""
        allergens = []
        for key, value in self.allergen_vector.items():
            if key.startswith('contains_') and value == 1:
                allergen = key.replace('contains_', '')
                allergens.append(allergen)
        return allergens
    
    # Sağlık göstergesi metodları
    def is_high_sugar(self):
        return self.health_indicators.get('high_sugar', 0) == 1
    
    def is_high_salt(self):
        return self.health_indicators.get('high_salt', 0) == 1
    
    def is_high_fat(self):
        return self.health_indicators.get('high_fat', 0) == 1
    
    def is_high_calorie(self):
        return self.health_indicators.get('high_calorie', 0) == 1
    
    def is_high_protein(self):
        return self.health_indicators.get('high_protein', 0) == 1
    
    def is_high_fiber(self):
        return self.health_indicators.get('high_fiber', 0) == 1
    
    # Analiz metodları
    def get_nutriscore_grade(self):
        return self.nutriscore_data.get('nutriscore_grade', None)
    
    def get_nutriscore_numeric(self):
        return self.nutriscore_data.get('nutriscore_numeric', None)
    
    def get_additives_count(self):
        return self.additives_info.get('additives_count', 0)
    
    def has_risky_additives(self):
        return self.additives_info.get('has_risky_additives', 0) == 1
    
    # ML özellikler için vektör oluşturma
    def get_feature_vector(self):
        """ML modeli için özellik vektörü döndürür"""
        features = {}
        
        # Besin değerleri
        features.update(self.nutrition_vector)
        
        # Makro oranları
        features.update(self.macro_ratios)
        
        # Binary özellikler
        features.update(self.allergen_vector)
        features.update(self.health_indicators)
        
        # Skalar değerler
        features['processing_level'] = self.processing_level
        features['nutrition_quality_score'] = self.nutrition_quality_score
        features['health_score'] = self.health_score
        features['additives_count'] = self.get_additives_count()
        features['ingredients_word_count'] = self.ingredients_word_count
        
        return features
    
    def to_dict(self):
        """Model verilerini dictionary formatında döndürür"""
        return {
            'product_code': self.product_code,
            'product_name': self.product_name,
            'main_category': self.main_category,
            'main_brand': self.main_brand,
            'nutrition_vector': self.nutrition_vector,
            'allergen_vector': self.allergen_vector,
            'additives_info': self.additives_info,
            'nutriscore_data': self.nutriscore_data,
            'processing_level': self.processing_level,
            'health_indicators': self.health_indicators,
            'nutrition_quality_score': self.nutrition_quality_score,
            'health_score': self.health_score,
            'macro_ratios': self.macro_ratios,
            'data_completeness_score': self.data_completeness_score,
            'is_valid_for_analysis': self.is_valid_for_analysis
        }


class ProductSimilarity(models.Model):
    """
    Ürünler arası benzerlik skorlarını saklar (öneri sistemi için)
    """
    product_1 = models.ForeignKey(ProductFeatures, on_delete=models.CASCADE, related_name='similarities_as_product1')
    product_2 = models.ForeignKey(ProductFeatures, on_delete=models.CASCADE, related_name='similarities_as_product2')
    
    # Farklı benzerlik türleri
    nutritional_similarity = models.FloatField(help_text="Besin değerleri benzerliği (0-1)")
    category_similarity = models.FloatField(help_text="Kategori benzerliği (0-1)")
    overall_similarity = models.FloatField(help_text="Genel benzerlik skoru (0-1)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'product_similarity'
        unique_together = ['product_1', 'product_2']
        indexes = [
            models.Index(fields=['overall_similarity']),
            models.Index(fields=['nutritional_similarity']),
        ]
    
    def __str__(self):
        return f"{self.product_1.product_name} - {self.product_2.product_name}: {self.overall_similarity:.2f}"