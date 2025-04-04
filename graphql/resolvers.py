import requests
from graphql_types import CartItemType, ProductType

# Fetch Cart data from the Cart service
def fetch_cart(user_id):
    try:
        response = requests.get(f"http://cart:5201/cart/{user_id}")
        response.raise_for_status()
        cart_data = response.json().get('cart', {})
        return [
            CartItemType(
                productId=item["productId"],
                name=item["Name"],
                category=item["Category"],  
                condition=item["Condition"],
                description=item["Description"],
                image_url=item["ImageURL"],
                price=item["Price"],
                sustainability_points=item["SustainabilityPoints"],
                tag_class=item["TagClass"],
                quantity=item["quantity"]
            )
            for item in cart_data.values()
        ]
    except requests.RequestException as e:
        print(f"Error fetching cart: {e}")
    return []

# Fetch Recommendations data from the Recommendation service
def fetch_recommendations(user_id):
    try:
        response = requests.get(f"http://recommendation:5204/recommendations/{user_id}")
        response.raise_for_status()
        recommendations = response.json().get('recommendations', [])
        return [
            ProductType(
                productId=item["productId"],
                name=item["Name"],
                category=item["Category"], 
                condition=item["Condition"],
                description=item["Description"],
                image_url=item["ImageURL"],
                price=item["Price"],
                sustainability_points=item["SustainabilityPoints"],
                tag_class=item["TagClass"],
            )
            for item in recommendations
        ]
    except requests.RequestException as e:
        print(f"Error fetching recommendations: {e}")
    return []
