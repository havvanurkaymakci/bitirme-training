# api/models/__init__.py

from .user_profile import User, Profile  
from .product_features import ProductFeatures, ProductSimilarity

__all__ = ['User', 'Profile', 'ProductFeatures', 'ProductSimilarity']