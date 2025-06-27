# api/serializers/product_serializers.py

from rest_framework import serializers
from api.models.product_features import ProductFeatures
from aimodels.ml_models.ml_recommendation_service import ml_recommendation_service
from aimodels.ml_models.ml_product_score_service import ml_product_score_service
# Profile serializer'ı import et
from api.serializers.profile_serializer import ProfileSerializer


class ProductFeaturesBaseSerializer(serializers.ModelSerializer):
    """
    Temel ürün özellikleri serializer - ML öneri sistemi için
    """
    # Besin değerleri - computed fields
    energy_kcal = serializers.SerializerMethodField()
    protein = serializers.SerializerMethodField()
    fat = serializers.SerializerMethodField()
    sugar = serializers.SerializerMethodField()
    salt = serializers.SerializerMethodField()
    fiber = serializers.SerializerMethodField()
    
    # Temel sağlık göstergeleri
    nutriscore_grade = serializers.SerializerMethodField()
    
    # Resim URL'i
    image_url = serializers.SerializerMethodField()
    
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
            'protein',
            'fat',
            'sugar',
            'salt',
            'fiber',
            'nutriscore_grade',
            'image_url',
        ]
        read_only_fields = ['id']
    
    def get_energy_kcal(self, obj):
        return obj.get_energy_kcal()
    
    def get_protein(self, obj):
        return obj.get_protein()
    
    def get_fat(self, obj):
        return obj.get_fat()
    
    def get_sugar(self, obj):
        return obj.get_sugar()
    
    def get_salt(self, obj):
        return obj.get_salt()
    
    def get_fiber(self, obj):
        return obj.get_fiber()
    
    def get_nutriscore_grade(self, obj):
        return obj.get_nutriscore_grade()
    
    def get_image_url(self, obj):
        """Ürün resmi URL'i oluştur"""
        if obj.product_code:
            code = str(obj.product_code)
            if len(code) >= 13:  # EAN-13 format
                folder_structure = '/'.join([code[i:i+3] for i in range(0, min(9, len(code)), 3)])
                return f"https://images.openfoodfacts.org/images/products/{folder_structure}/{code}/front_en.jpg"
            else:
                return f"https://images.openfoodfacts.org/images/products/{code}/front_en.jpg"
        return "https://via.placeholder.com/150x150?text=No+Image"


class ProductRecommendationSerializer(ProductFeaturesBaseSerializer):
    """
    ML tabanlı ürün önerileri için serializer
    """
    # ML recommendation service'in döndürdüğü alanlarla uyumlu
    final_score = serializers.FloatField(read_only=True)
    ml_score = serializers.FloatField(read_only=True)
    target_score = serializers.FloatField(read_only=True)
    score_improvement = serializers.FloatField(read_only=True)
    similarity_bonus = serializers.FloatField(read_only=True)
    improvement_bonus = serializers.FloatField(read_only=True)
    reason = serializers.CharField(read_only=True)
    category_match = serializers.BooleanField(read_only=True)
    
    # Backward compatibility için eski alanlar
    personalized_score = serializers.SerializerMethodField()
    recommendation_reason = serializers.SerializerMethodField()
    
    class Meta(ProductFeaturesBaseSerializer.Meta):
        fields = ProductFeaturesBaseSerializer.Meta.fields + [
            'final_score',
            'ml_score',
            'target_score',
            'score_improvement',
            'similarity_bonus',
            'improvement_bonus',
            'reason',
            'category_match',
            'personalized_score',  # backward compatibility
            'recommendation_reason',  # backward compatibility
        ]
    
    def get_personalized_score(self, obj):
        """Backward compatibility için"""
        return getattr(obj, 'final_score', None)
    
    def get_recommendation_reason(self, obj):
        """Backward compatibility için"""
        return getattr(obj, 'reason', '')


class ProductSearchSerializer(serializers.Serializer):
    """
    ML tabanlı ürün arama ve öneri parametreleri
    """
    # Temel arama
    query = serializers.CharField(max_length=200, required=False, allow_blank=True)
    category = serializers.CharField(max_length=200, required=False, allow_blank=True)
    brand = serializers.CharField(max_length=200, required=False, allow_blank=True)
    
    # Sayfalama
    page = serializers.IntegerField(min_value=1, default=1)
    page_size = serializers.IntegerField(min_value=1, max_value=50, default=20)
    
    # Sıralama
    sort_by = serializers.ChoiceField(
        choices=[
            'relevance',
            'personalized_score', 
            'nutrition_quality_score',
            'health_score',
            'product_name'
        ],
        default='relevance',
        required=False
    )
    
    # Kişiselleştirme
    include_personalized_scores = serializers.BooleanField(default=True)
    
    def validate(self, data):
        # En az bir arama kriteri olmalı
        if not any([data.get('query'), data.get('category'), data.get('brand')]):
            raise serializers.ValidationError(
                "En az bir arama kriteri belirtmelisiniz"
            )
        return data


class ProductAlternativesSerializer(serializers.Serializer):
    """
    Alternatif ürün önerileri için serializer
    """
    product_code = serializers.CharField(max_length=50)
    limit = serializers.IntegerField(min_value=1, max_value=20, default=5)
    min_score_threshold = serializers.FloatField(min_value=0.0, max_value=10.0, default=6.0)
    
    def validate_product_code(self, value):
        try:
            ProductFeatures.objects.get(product_code=value, is_valid_for_analysis=True)
        except ProductFeatures.DoesNotExist:
            raise serializers.ValidationError("Ürün bulunamadı veya analiz için geçerli değil")
        return value


class ProductAlternativesResponseSerializer(serializers.Serializer):
    """
    ML recommendation service yanıtına uygun serializer
    """
    alternatives = ProductRecommendationSerializer(many=True, read_only=True)
    target_product = serializers.DictField(read_only=True)
    recommendation_stats = serializers.DictField(read_only=True)


class PersonalizedProductScoreSerializer(serializers.Serializer):
    """
    Kişiselleştirilmiş ürün skoru için serializer
    """
    product_code = serializers.CharField(max_length=50)
    
    def validate_product_code(self, value):
        try:
            ProductFeatures.objects.get(product_code=value, is_valid_for_analysis=True)
        except ProductFeatures.DoesNotExist:
            raise serializers.ValidationError("Ürün bulunamadı veya analiz için geçerli değil")
        return value


class PersonalizedProductScoreResponseSerializer(serializers.Serializer):
    """
    ML score service yanıtına uygun serializer
    """
    personalized_score = serializers.FloatField(read_only=True)
    score_level = serializers.DictField(read_only=True)
    analysis = serializers.DictField(read_only=True)
    product_info = serializers.DictField(read_only=True)


# ML modeli için profil verilerini almak amacıyla ProfileSerializer'ı kullan
class MLUserProfileInputSerializer(serializers.Serializer):
    """
    ML modeli için optimize edilmiş kullanıcı profili input serializer
    ML servislerinin beklediği alanlarla tam uyumlu
    """
    # Temel demografik bilgiler
    age = serializers.IntegerField(min_value=1, max_value=120)
    gender = serializers.ChoiceField(choices=['Male', 'Female', 'Other'])
    height = serializers.FloatField(min_value=50, max_value=300)  # cm
    weight = serializers.FloatField(min_value=20, max_value=500)  # kg
    bmi = serializers.FloatField(required=False)
    activity_level = serializers.ChoiceField(
        choices=['low', 'moderate', 'high'],
        default='moderate'
    )
    
    # Sağlık durumu - ML modelin beklediği alanlarla uyumlu
    medical_conditions = serializers.ListField(
        child=serializers.ChoiceField(choices=[
            'diabetes_type_2',
            'chronic_kidney_disease', 
            'hyperthyroidism',
            'osteoporosis',
            'hypertension',
            'cardiovascular_disease'
        ]),
        default=list,
        required=False
    )
    
    allergies = serializers.ListField(
        child=serializers.CharField(),
        default=list,
        required=False
    )
    
    # Diyet tercihleri - ML modelin beklediği alanlarla uyumlu
    dietary_preferences = serializers.ListField(
        child=serializers.ChoiceField(choices=[
            'high_protein',
            'low_fat',
            'vegan',
            'vegetarian',
            'gluten_free',
            'low_sodium'
        ]),
        default=list,
        required=False
    )
    
    # Sağlık hedefleri - ML modelin beklediği alanlarla uyumlu
    health_goals = serializers.ListField(
        child=serializers.ChoiceField(choices=[
            'muscle_gain',
            'heart_health',
            'boost_energy',
            'weight_loss',
            'weight_gain',
            'better_digestion'
        ]),
        default=list,
        required=False
    )
    
    def validate(self, data):
        # BMI hesapla eğer verilmemişse
        if not data.get('bmi') and data.get('height') and data.get('weight'):
            height_m = data['height'] / 100
            data['bmi'] = round(data['weight'] / (height_m ** 2), 1)
        
        return data
    
    @classmethod
    def from_profile(cls, profile):
        """
        ProfileSerializer instance'ından ML input data'sı oluştur
        """
        return {
            'age': profile.age,
            'gender': profile.gender,
            'height': profile.height,
            'weight': profile.weight,
            'bmi': profile.bmi,
            'activity_level': getattr(profile, 'activity_level', 'moderate'),
            'medical_conditions': profile.medical_conditions or [],
            'allergies': profile.allergies or [],
            'dietary_preferences': profile.dietary_preferences or [],
            'health_goals': getattr(profile, 'health_goals', []),
        }


class ProductListWithScoresSerializer(serializers.Serializer):
    """
    Kişiselleştirilmiş skorlu ürün listesi için serializer
    """
    products = ProductRecommendationSerializer(many=True, read_only=True)
    total_count = serializers.IntegerField(read_only=True)
    page = serializers.IntegerField(read_only=True)
    page_size = serializers.IntegerField(read_only=True)
    has_next = serializers.BooleanField(read_only=True)
    has_previous = serializers.BooleanField(read_only=True)


class ProductComparisonSerializer(serializers.Serializer):
    """
    Ürün karşılaştırması için serializer
    """
    product_codes = serializers.ListField(
        child=serializers.CharField(max_length=50),
        min_length=2,
        max_length=5
    )
    
    def validate_product_codes(self, value):
        # Tüm ürünlerin mevcut olduğunu kontrol et
        for code in value:
            try:
                ProductFeatures.objects.get(product_code=code, is_valid_for_analysis=True)
            except ProductFeatures.DoesNotExist:
                raise serializers.ValidationError(f"Ürün bulunamadı: {code}")
        return value


class ProductComparisonResponseSerializer(serializers.Serializer):
    """
    Ürün karşılaştırması yanıt serializer
    """
    products = ProductRecommendationSerializer(many=True, read_only=True)
    comparison_summary = serializers.DictField(read_only=True)
    best_match = serializers.DictField(read_only=True)


class HealthAnalysisSerializer(serializers.Serializer):
    """
    Sağlık analizi yanıt serializer - ML score service analysis ile uyumlu
    """
    product = ProductFeaturesBaseSerializer(read_only=True)
    personalized_score = serializers.FloatField(read_only=True)
    score_level = serializers.DictField(read_only=True)
    positive_points = serializers.ListField(
        child=serializers.CharField(),
        read_only=True
    )
    negative_points = serializers.ListField(
        child=serializers.CharField(),
        read_only=True
    )
    recommendations = serializers.ListField(
        child=serializers.CharField(),
        read_only=True
    )


# Utility serializers
class SuccessResponseSerializer(serializers.Serializer):
    """Başarılı işlem yanıtı için serializer"""
    success = serializers.BooleanField(default=True)
    message = serializers.CharField()
    data = serializers.DictField(required=False)


class ErrorResponseSerializer(serializers.Serializer):
    """Hata yanıtı için serializer"""
    success = serializers.BooleanField(default=False)
    error = serializers.CharField()
    details = serializers.DictField(required=False)