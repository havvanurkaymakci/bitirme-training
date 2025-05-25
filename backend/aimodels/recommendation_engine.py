# backend/aimodels/recommendation_engine.py

def analyze_products_for_user(profile, data):
    products = data.get('products', [])
    allergies = (profile.allergies or '').lower().split(',') if profile.allergies else []
    medical_conditions = (profile.medical_conditions or '').lower().split(',') if profile.medical_conditions else []
    diet_pref = (profile.dietary_preferences or '').lower().strip() if profile.dietary_preferences else ''

    warnings = []
    recommended = []

    for product in products:
        ingredients = (product.get('ingredients_text') or '').lower()
        labels = [label.lower() for label in product.get('labels_tags', [])]
        name = product.get('product_name', 'Unknown')

        # Alerji uyarıları
        for allergen in allergies:
            allergen = allergen.strip()
            if allergen and allergen in ingredients:
                warnings.append({
                    'product': name,
                    'warning': f'Contains allergen: {allergen}'
                })

        # Diyet tercihi kontrolü (örneğin vegan ise vegan olmayanları dışla)
        if diet_pref == 'vegan' and 'en:vegan' not in labels:
            continue
        if diet_pref == 'vegetarian' and 'en:vegetarian' not in labels:
            continue

        # Basit öneri kriteri: Nutriscore A veya B olanları öner
        nutriscore = product.get('nutriscore_grade', '').upper()
        if nutriscore in ['A', 'B']:
            recommended.append(product)

        # Örnek: Diyabet varsa yüksek şekerli ürünler uyarısı
        if 'diabetes' in medical_conditions:
            sugars = product.get('nutriments', {}).get('sugars_100g', 0)
            if sugars and sugars > 5:  # 5 gram şeker sınırı örneği
                warnings.append({
                    'product': name,
                    'warning': 'High sugar content, not recommended for diabetics.'
                })

    return {
        'recommended_products': recommended,
        'warnings': warnings,
        'all_products': products
    }
