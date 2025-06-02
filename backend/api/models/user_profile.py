# user_profile.py
from django.db import models
from django.db.models.signals import post_save
from django.contrib.auth.models import AbstractUser
from .product_features import ProductFeatures, ProductSimilarity


class User(AbstractUser):
    username = models.CharField(max_length=100)
    email = models.EmailField(unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    #def profile(self):
        #return Profile.objects.get(user=self)

class Profile(models.Model):
    # Medical Conditions Choices
    MEDICAL_CONDITIONS_CHOICES = [
        # Metabolik / Endokrin
        ('diabetes_type_1', 'Tip 1 Diyabet'),
        ('diabetes_type_2', 'Tip 2 Diyabet'),
        ('prediabetes', 'Prediabetes'),
        ('insulin_resistance', 'İnsülin Direnci'),
        ('hypoglycemia', 'Düşük Kan Şekeri'),
        ('hypothyroidism', 'Hipotiroidi'),
        ('hyperthyroidism', 'Hipertiroidi'),
        ('pcos', 'Polikistik Over Sendromu'),
        # Kardiyovasküler
        ('hypertension', 'Yüksek Tansiyon'),
        ('high_cholesterol', 'Yüksek Kolesterol'),
        ('heart_disease', 'Kalp Hastalığı'),
        # Gastrointestinal
        ('celiac_disease', 'Çölyak Hastalığı'),
        ('irritable_bowel_syndrome', 'IBS'),
        ('inflammatory_bowel_disease', 'IBD (Crohn, Ülseratif Kolit)'),
        ('acid_reflux', 'Reflü'),
        ('lactose_intolerance', 'Laktoz İntoleransı'),
        # Hormonal / Kadın Sağlığı
        ('pregnancy', 'Hamilelik'),
        ('breastfeeding', 'Emzirme'),
        ('menopause', 'Menopoz'),
        # Ağırlık / Yeme Bozuklukları
        ('obesity', 'Obezite'),
        ('underweight', 'Zayıflık'),
        ('binge_eating_disorder', 'Tıkınırcasına Yeme Bozukluğu'),
        ('anorexia', 'Anoreksiya'),
        ('bulimia', 'Bulimia'),
        # Diğer
        ('anemia', 'Kansızlık'),
        ('osteoporosis', 'Kemik Erimesi'),
        ('chronic_kidney_disease', 'Kronik Böbrek Hastalığı'),
        ('fatty_liver', 'Karaciğer Yağlanması'),
        ('gout', 'Gut'),
    ]

    # Allergies Choices
    ALLERGIES_CHOICES = [
        ('peanuts', 'Yer fıstığı'),
        ('tree_nuts', 'Badem, ceviz, fındık vs.'),
        ('milk', 'Süt'),
        ('eggs', 'Yumurta'),
        ('wheat', 'Buğday'),
        ('soy', 'Soya'),
        ('fish', 'Balık'),
        ('shellfish', 'Karides, midye vs.'),
        ('lactose', 'Laktoz'),
        ('gluten', 'Gluten'),
        ('sesame', 'Susam'),
        ('corn', 'Mısır'),
        ('food_dyes', 'Gıda boyaları'),
        ('preservatives', 'Koruyucular (sodyum benzoat, vb.)'),
    ]

    # Dietary Preferences Choices
    DIETARY_PREFERENCES_CHOICES = [
        ('vegan', 'Vegan'),
        ('vegetarian', 'Vejetaryen'),
        ('pescatarian', 'Sadece balık tüketen'),
        ('flexitarian', 'Esnek ve çoğunlukla bitkisel'),
        ('gluten_free', 'Glütensiz'),
        ('lactose_free', 'Laktozsuz'),
        ('low_fodmap', 'Düşük FODMAP'),
        ('ketogenic', 'Ketojenik'),
        ('paleo', 'Paleo'),
        ('mediterranean', 'Akdeniz'),
        ('dash', 'Hipertansiyona karşı beslenme'),
        ('diabetic_friendly', 'Diyabetik dostu'),
        ('heart_healthy', 'Kalp sağlığı'),
        ('low_carb', 'Düşük karbonhidrat'),
        ('high_protein', 'Yüksek protein'),
        ('low_fat', 'Düşük yağ'),
        ('low_sodium', 'Düşük sodyum'),
        ('halal', 'Helal'),
        ('kosher', 'Koşer'),
        ('intermittent_fasting', 'Aralıklı oruç'),
        ('no_preference', 'Tercih yok'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=1000)
    age = models.IntegerField(default=18)
    gender = models.CharField(max_length=10, null=True)  # Example: 'Male', 'Female', 'Other'
    height = models.FloatField(null=True)  # in cm
    weight = models.FloatField(null=True)  # in kg
    bmi = models.FloatField(blank=True, null=True)  # BMI value (calculated)
    
    # Changed to JSONField to store multiple selections
    medical_conditions = models.JSONField(default=list, blank=True)  # List of condition keys
    allergies = models.JSONField(default=list, blank=True)  # List of allergy keys
    dietary_preferences = models.JSONField(default=list, blank=True)  # List of dietary preference keys
    
    # Views.py'de kullanılan ekstra alanlar - bu alanlar yoksa ekleyin
    activity_level = models.CharField(max_length=20, default='moderate', 
                                    choices=[('low', 'Düşük'), ('moderate', 'Orta'), ('high', 'Yüksek')])
    health_goals = models.JSONField(default=list, blank=True)  # List of health goals

    def save(self, *args, **kwargs):
        if self.weight and self.height:
            self.bmi = self.weight / (self.height / 100) ** 2
        super().save(*args, **kwargs)

    def get_medical_conditions_display(self):
        """Return display names for medical conditions"""
        if not self.medical_conditions:
            return []
        conditions_dict = dict(self.MEDICAL_CONDITIONS_CHOICES)
        return [conditions_dict.get(condition, condition) for condition in self.medical_conditions]

    def get_allergies_display(self):
        """Return display names for allergies"""
        if not self.allergies:
            return []
        allergies_dict = dict(self.ALLERGIES_CHOICES)
        return [allergies_dict.get(allergy, allergy) for allergy in self.allergies]

    def get_dietary_preferences_display(self):
        """Return display names for dietary preferences"""
        if not self.dietary_preferences:
            return []
        preferences_dict = dict(self.DIETARY_PREFERENCES_CHOICES)
        return [preferences_dict.get(pref, pref) for pref in self.dietary_preferences]

    def __str__(self):
        return self.full_name


def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

post_save.connect(create_user_profile, sender=User)
post_save.connect(save_user_profile, sender=User)