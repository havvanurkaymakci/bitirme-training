# api/models.py

# Import all models from subdirectories
from .models.user_profile import User, Profile
from .models.product_features import ProductFeatures, ProductSimilarity

# Make sure Django can find these models
__all__ = ['User', 'Profile', 'ProductFeatures', 'ProductSimilarity']