def apply_filters(products, filters):
    def match(product):
        nutriments = product.get('nutriments', {})
        ingredients = product.get('ingredients_text', '') or ''
        labels_tags = product.get('labels_tags', [])
        additives_tags = product.get('additives_tags', [])
        categories_tags = product.get('categories_tags', [])

        # Enerji (kalori) aralığı
        if filters.get('min_energy_kcal', '') != '':
            if nutriments.get('energy-kcal_100g', 0) < float(filters['min_energy_kcal']):
                return False
        if filters.get('max_energy_kcal', '') != '':
            if nutriments.get('energy-kcal_100g', 0) > float(filters['max_energy_kcal']):
                return False
        
        # max_sugar filtresi kontrolü
        if 'max_sugar' in filters and filters['max_sugar'] != '':
            value = nutriments.get('sugars_100g')
            if value is None or value > float(filters['max_sugar']):
                return False

        # Diğer besin filtreleri de aynı şekilde kontrol edilmeli:
        if 'max_fat' in filters and filters['max_fat'] != '':
            if nutriments.get('fat_100g', 0) > float(filters['max_fat']):
                return False
        if 'max_saturated_fat' in filters and filters['max_saturated_fat'] != '':
            if nutriments.get('saturated-fat_100g', 0) > float(filters['max_saturated_fat']):
                return False
        if 'max_salt' in filters and filters['max_salt'] != '':
            if nutriments.get('salt_100g', 0) > float(filters['max_salt']):
                return False
        if 'max_sodium' in filters and filters['max_sodium'] != '':
            if nutriments.get('sodium_100g', 0) > float(filters['max_sodium']):
                return False
        if 'min_fiber' in filters and filters['min_fiber'] != '':
            if nutriments.get('fiber_100g', 0) < float(filters['min_fiber']):
                return False
        if 'min_proteins' in filters and filters['min_proteins'] != '':
            if nutriments.get('proteins_100g', 0) < float(filters['min_proteins']):
                return False
        if 'max_proteins' in filters and filters['max_proteins'] != '':
            if nutriments.get('proteins_100g', 0) > float(filters['max_proteins']):
                return False
            
        # Katkı maddeleri
        if 'additives' in filters and filters['additives']:
            additives_filter = [a.strip().lower() for a in filters['additives'].split(',')]
            if not any(additive.lower() in additives_tags for additive in additives_filter):
                return False
        
        # Kategoriler
        if 'categories' in filters and filters['categories']:
            categories_filter = [c.strip().lower() for c in filters['categories'].split(',')]
            if not any(category.lower() in categories_tags for category in categories_filter):
                return False

        # İçerik filtreleri
        for excluded in filters.get('exclude_ingredients', []):
            if excluded.lower() in ingredients.lower():
                return False
        for required in filters.get('include_ingredients', []):
            if required.lower() not in ingredients.lower():
                return False

        # Etiket bazlı filtreler
        if filters.get('is_vegan', False):
            if 'vegan' not in labels_tags:
                return False
        if filters.get('is_vegetarian', False):
            if 'vegetarian' not in labels_tags:
                return False
        if 'nutriscore_grade' in filters and filters['nutriscore_grade']:
            grades = [g.strip().upper() for g in filters['nutriscore_grade'].split(',')]
            if product.get('nutriscore_grade', '').upper() not in grades:
                return False
        if 'nova_group' in filters and filters['nova_group']:
            nova_groups = [int(n.strip()) for n in filters['nova_group'].split(',') if n.strip().isdigit()]
            if product.get('nova_group') not in nova_groups:
                return False

        return True

    return [product for product in products if match(product)]
