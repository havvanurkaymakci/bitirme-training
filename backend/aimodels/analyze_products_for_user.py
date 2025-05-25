# advisors/recommendation_engine.py

def analyze_products_for_user(profile, product_data):
    # Gelecekte burası yapay zekaya bağlanacak
    # Şimdilik örnek filtreleme: alerjiye göre filtrele
    allergies = [a.strip().lower() for a in (profile.allergies or "").split(",")]

    filtered_products = []
    for product in product_data.get("products", []):
        ingredients = product.get("ingredients_text", "").lower()
        warning = any(allergen in ingredients for allergen in allergies)
        product["warning"] = warning
        product["advice"] = "Avoid this product due to your allergies" if warning else "Safe to consume"
        filtered_products.append(product)

    return {
        "products": filtered_products,
        "user": profile.full_name,
        "filters_applied": True,
        "total": len(filtered_products)
    }
