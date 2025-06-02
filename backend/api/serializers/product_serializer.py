# api/serializers/product_serializers.py

from rest_framework import serializers
from api.models.product_features import ProductFeatures, ProductSimilarity


class ProductFeaturesSerializer(serializers.ModelSerializer):
    """
    ProductFeatures modeli için ana serializer
    """
    # Computed fields - sadece okuma için
    energy_kcal = serializers.SerializerMethodField()
    fat = serializers.SerializerMethodField()
    sugar = serializers.SerializerMethodField()
    salt = serializers.SerializerMethodField()
    protein = serializers.SerializerMethodField()
    fiber = serializers.SerializerMethodField()
    
    # Alerjen bilgileri
    all_allergens = serializers.SerializerMethodField()
    
    # Sağlık göstergeleri
    high_sugar = serializers.SerializerMethodField()
    high_salt = serializers.SerializerMethodField()
    high_fat = serializers.SerializerMethodField()
    high_calorie = serializers.SerializerMethodField()
    high_protein = serializers.SerializerMethodField()
    high_fiber = serializers.SerializerMethodField()
    
    # Nutriscore bilgileri
    nutriscore_grade = serializers.SerializerMethodField()
    nutriscore_numeric = serializers.SerializerMethodField()
    
    # Katkı madde bilgileri
    additives_count = serializers.SerializerMethodField()
    has_risky_additives = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductFeatures
        fields = [
            # Ana ürün bilgileri
            'id',
            'product_code',
            'product_name',
            'main_category',
            'main_brand',
            'main_country',
            
            # JSON alanları
            'nutrition_vector',
            'allergen_vector',
            'additives_info',
            'nutriscore_data',
            'health_indicators',
            'macro_ratios',
            
            # Skalar alanlar
            'processing_level',
            'nutrition_quality_score',
            'health_score',
            'data_completeness_score',
            'is_valid_for_analysis',
            
            # Text alanları
            'ingredients_text',
            'ingredients_text_length',
            'ingredients_word_count',
            
            # Computed fields
            'energy_kcal',
            'fat',
            'sugar',
            'salt',
            'protein',
            'fiber',
            'all_allergens',
            'high_sugar',
            'high_salt',
            'high_fat',
            'high_calorie',
            'high_protein',
            'high_fiber',
            'nutriscore_grade',
            'nutriscore_numeric',
            'additives_count',
            'has_risky_additives',
            
            # Zaman damgaları
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'updated_at',
            # Computed fields read-only
            'energy_kcal',
            'fat',
            'sugar',
            'salt',
            'protein',
            'fiber',
            'all_allergens',
            'high_sugar',
            'high_salt',
            'high_fat',
            'high_calorie',
            'high_protein',
            'high_fiber',
            'nutriscore_grade',
            'nutriscore_numeric',
            'additives_count',
            'has_risky_additives',
        ]
    
    # Besin değeri getter metodları
    def get_energy_kcal(self, obj):
        return obj.get_energy_kcal()
    
    def get_fat(self, obj):
        return obj.get_fat()
    
    def get_sugar(self, obj):
        return obj.get_sugar()
    
    def get_salt(self, obj):
        return obj.get_salt()
    
    def get_protein(self, obj):
        return obj.get_protein()
    
    def get_fiber(self, obj):
        return obj.get_fiber()
    
    # Alerjen bilgileri
    def get_all_allergens(self, obj):
        return obj.get_all_allergens()
    
    # Sağlık göstergeleri
    def get_high_sugar(self, obj):
        return obj.is_high_sugar()
    
    def get_high_salt(self, obj):
        return obj.is_high_salt()
    
    def get_high_fat(self, obj):
        return obj.is_high_fat()
    
    def get_high_calorie(self, obj):
        return obj.is_high_calorie()
    
    def get_high_protein(self, obj):
        return obj.is_high_protein()
    
    def get_high_fiber(self, obj):
        return obj.is_high_fiber()
    
    # Nutriscore bilgileri
    def get_nutriscore_grade(self, obj):
        return obj.get_nutriscore_grade()
    
    def get_nutriscore_numeric(self, obj):
        return obj.get_nutriscore_numeric()
    
    # Katkı madde bilgileri
    def get_additives_count(self, obj):
        return obj.get_additives_count()
    
    def get_has_risky_additives(self, obj):
        return obj.has_risky_additives()


class ProductFeaturesListSerializer(serializers.ModelSerializer):
    """
    Liste görünümü için optimize edilmiş serializer - daha az alan
    """
    energy_kcal = serializers.SerializerMethodField()
    nutriscore_grade = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductFeatures
        fields = [
            'id',
            'product_code',
            'product_name',
            'main_category',
            'main_brand',
            'processing_level',
            'nutrition_quality_score',
            'health_score',
            'energy_kcal',
            'nutriscore_grade',
            'is_valid_for_analysis',
        ]
    
    def get_energy_kcal(self, obj):
        return obj.get_energy_kcal()
    
    def get_nutriscore_grade(self, obj):
        return obj.get_nutriscore_grade()


class ProductFeaturesDetailSerializer(ProductFeaturesSerializer):
    """
    Detay görünümü için genişletilmiş serializer
    """
    feature_vector = serializers.SerializerMethodField()
    
    class Meta(ProductFeaturesSerializer.Meta):
        fields = ProductFeaturesSerializer.Meta.fields + ['feature_vector']
    
    def get_feature_vector(self, obj):
        return obj.get_feature_vector()


class ProductSimilaritySerializer(serializers.ModelSerializer):
    """
    Ürün benzerlik skorları için serializer
    """
    product_1_name = serializers.CharField(source='product_1.product_name', read_only=True)
    product_2_name = serializers.CharField(source='product_2.product_name', read_only=True)
    product_1_code = serializers.CharField(source='product_1.product_code', read_only=True)
    product_2_code = serializers.CharField(source='product_2.product_code', read_only=True)
    
    class Meta:
        model = ProductSimilarity
        fields = [
            'id',
            'product_1',
            'product_2',
            'product_1_name',
            'product_2_name',
            'product_1_code',
            'product_2_code',
            'nutritional_similarity',
            'category_similarity',
            'overall_similarity',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class ProductRecommendationSerializer(serializers.ModelSerializer):
    """
    Öneri sistemi için özel serializer
    """
    similarity_score = serializers.FloatField(read_only=True)
    recommendation_reason = serializers.CharField(read_only=True)
    
    class Meta:
        model = ProductFeatures
        fields = [
            'id',
            'product_code',
            'product_name',
            'main_category',
            'main_brand',
            'nutrition_quality_score',
            'health_score',
            'processing_level',
            'similarity_score',
            'recommendation_reason',
        ]


class ProductSearchSerializer(serializers.Serializer):
    """
    Ürün arama parametreleri için serializer
    """
    query = serializers.CharField(max_length=200, required=False, allow_blank=True)
    category = serializers.CharField(max_length=200, required=False, allow_blank=True)
    brand = serializers.CharField(max_length=200, required=False, allow_blank=True)
    min_nutrition_score = serializers.FloatField(min_value=0, max_value=10, required=False)
    max_nutrition_score = serializers.FloatField(min_value=0, max_value=10, required=False)
    processing_level = serializers.ChoiceField(
        choices=[1, 2, 3, 4], 
        required=False
    )
    allergens_to_avoid = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        allow_empty=True
    )
    health_indicators = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        allow_empty=True
    )
    nutriscore_grades = serializers.ListField(
        child=serializers.CharField(max_length=1),
        required=False,
        allow_empty=True
    )
    
    def validate(self, data):
        """Arama parametrelerini doğrula"""
        min_score = data.get('min_nutrition_score')
        max_score = data.get('max_nutrition_score')
        
        if min_score is not None and max_score is not None:
            if min_score > max_score:
                raise serializers.ValidationError(
                    "min_nutrition_score, max_nutrition_score'dan büyük olamaz"
                )
        
        return data


class ProductComparisonSerializer(serializers.Serializer):
    """
    Ürün karşılaştırması için serializer
    """
    product_codes = serializers.ListField(
        child=serializers.CharField(max_length=50),
        min_length=2,
        max_length=5,
        help_text="Karşılaştırılacak ürün kodları (2-5 arasında)"
    )
    
    comparison_fields = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=['nutrition_quality_score', 'health_score', 'processing_level'],
        help_text="Karşılaştırılacak alanlar"
    )


class ProductAnalysisSerializer(serializers.Serializer):
    """
    Ürün analizi sonuçları için serializer
    """
    product = ProductFeaturesDetailSerializer(read_only=True)
    health_warnings = serializers.ListField(
        child=serializers.CharField(),
        read_only=True
    )
    dietary_warnings = serializers.ListField(
        child=serializers.CharField(),
        read_only=True
    )
    allergy_warnings = serializers.ListField(
        child=serializers.CharField(),
        read_only=True
    )
    recommendations = serializers.ListField(
        child=ProductRecommendationSerializer(),
        read_only=True
    )
    nutritional_analysis = serializers.DictField(read_only=True)
    overall_rating = serializers.FloatField(read_only=True)
    rating_explanation = serializers.CharField(read_only=True)


class BulkProductCreateSerializer(serializers.Serializer):
    """
    Toplu ürün ekleme için serializer
    """
    products = serializers.ListField(
        child=ProductFeaturesSerializer(),
        min_length=1,
        max_length=1000
    )
    
    def create(self, validated_data):
        """Toplu ürün oluşturma"""
        products_data = validated_data['products']
        products = []
        
        for product_data in products_data:
            product = ProductFeatures.objects.create(**product_data)
            products.append(product)
        
        return {'products': products, 'count': len(products)}


class ProductStatsSerializer(serializers.Serializer):
    """
    Ürün istatistikleri için serializer
    """
    total_products = serializers.IntegerField(read_only=True)
    categories = serializers.DictField(read_only=True)
    brands = serializers.DictField(read_only=True)
    processing_levels = serializers.DictField(read_only=True)
    nutriscore_distribution = serializers.DictField(read_only=True)
    average_nutrition_score = serializers.FloatField(read_only=True)
    average_health_score = serializers.FloatField(read_only=True)