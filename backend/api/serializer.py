# serializer.py
from api.models import User, Profile
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email')


class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    
    # Add display fields for better frontend usage
    medical_conditions_display = serializers.SerializerMethodField()
    allergies_display = serializers.SerializerMethodField()
    dietary_preferences_display = serializers.SerializerMethodField()
    
    # Add choices fields for frontend dropdowns
    medical_conditions_choices = serializers.SerializerMethodField()
    allergies_choices = serializers.SerializerMethodField()
    dietary_preferences_choices = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = (
            'id', 'username', 'email', 'full_name',
            'age', 'gender', 'height', 'weight', 'bmi', 
            'medical_conditions', 'allergies', 'dietary_preferences',
            'activity_level', 'health_goals',  # Yeni alanlar eklendi
            'medical_conditions_display', 'allergies_display', 'dietary_preferences_display',
            'medical_conditions_choices', 'allergies_choices', 'dietary_preferences_choices'
        )

    def get_username(self, obj):
        return obj.user.username

    def get_email(self, obj):
        return obj.user.email

    def get_medical_conditions_display(self, obj):
        return obj.get_medical_conditions_display()

    def get_allergies_display(self, obj):
        return obj.get_allergies_display()

    def get_dietary_preferences_display(self, obj):
        return obj.get_dietary_preferences_display()

    def get_medical_conditions_choices(self, obj):
        return Profile.MEDICAL_CONDITIONS_CHOICES

    def get_allergies_choices(self, obj):
        return Profile.ALLERGIES_CHOICES

    def get_dietary_preferences_choices(self, obj):
        return Profile.DIETARY_PREFERENCES_CHOICES

    def validate_medical_conditions(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Medical conditions must be a list")
        
        valid_choices = [choice[0] for choice in Profile.MEDICAL_CONDITIONS_CHOICES]
        for condition in value:
            if condition not in valid_choices:
                raise serializers.ValidationError(f"Invalid medical condition: {condition}")
        return value

    def validate_allergies(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Allergies must be a list")
        
        valid_choices = [choice[0] for choice in Profile.ALLERGIES_CHOICES]
        for allergy in value:
            if allergy not in valid_choices:
                raise serializers.ValidationError(f"Invalid allergy: {allergy}")
        return value

    def validate_dietary_preferences(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Dietary preferences must be a list")
        
        valid_choices = [choice[0] for choice in Profile.DIETARY_PREFERENCES_CHOICES]
        for preference in value:
            if preference not in valid_choices:
                raise serializers.ValidationError(f"Invalid dietary preference: {preference}")
        return value
    
    # Yeni alanlar için validasyonlar
    def validate_health_goals(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Health goals must be a list")
        return value


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Profile yoksa hata almamak için try-except kullanın
        try:
            profile = user.profile
            token['full_name'] = profile.full_name
            token['username'] = user.username
            token['email'] = user.email
            token['age'] = profile.age
            token['gender'] = profile.gender
            token['height'] = profile.height
            token['weight'] = profile.weight
            token['bmi'] = profile.bmi
            token['medical_conditions'] = profile.medical_conditions
            token['allergies'] = profile.allergies
            token['dietary_preferences'] = profile.dietary_preferences
            token['activity_level'] = getattr(profile, 'activity_level', 'moderate')  # Yeni alan
            token['health_goals'] = getattr(profile, 'health_goals', [])  # Yeni alan
        except Profile.DoesNotExist:
            # Profile yoksa varsayılan değerler
            token['full_name'] = user.username
            token['username'] = user.username
            token['email'] = user.email
            token['age'] = 18
            token['gender'] = None
            token['height'] = None
            token['weight'] = None
            token['bmi'] = None
            token['medical_conditions'] = []
            token['allergies'] = []
            token['dietary_preferences'] = []
            token['activity_level'] = 'moderate'
            token['health_goals'] = []
        
        return token


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('email', 'username', 'password', 'password2')

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError(
                {"password": "Password fields didn't match."})

        return attrs

    def create(self, validated_data):
        user = User.objects.create(
            username=validated_data['username'],
            email=validated_data['email']
        )
        user.set_password(validated_data['password'])
        user.save()
        return user