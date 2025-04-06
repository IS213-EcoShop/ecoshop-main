from flask import Flask, request, jsonify
from supabase import create_client, Client
from dotenv import load_dotenv
import threading
import os
import random
import json
from utils.invokes import invoke_http  # Your HTTP utility function
import utils.amqp_lib as rabbit
from utils.cors_config import enable_cors

# RabbitMQ Connection Details
RABBITMQ_HOST = 'rabbitmq'
RABBITMQ_PORT = 5672
RECOMMENDATION_QUEUE_NAME = "recommendation_queue"
PLACE_ORDER_EXCHANGE_NAME = "place_order_exchange"

# Load environment variables
load_dotenv()

app = Flask(__name__)
enable_cors(app)

# Initialize Supabase
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# External API endpoint for fetching all products
PRODUCTS_API_URL = "https://personal-o2kymv2n.outsystemscloud.com/SustainaMart/rest/v1/allproducts/"

# External API endpoint for fetching single product details
SINGLE_API_URL = "https://personal-o2kymv2n.outsystemscloud.com/SustainaMart/rest/v1/products/{productid}/"\

# External API endpoint for fetching cart details to compare
CART_API_URL = "http://cart:5201/cart/{user_id}"

# Function to get user TagClass preferences based on quantity purchased
def get_user_tags(user_id):
    response = supabase.table('user_purchases').select('products').eq('user_id', user_id).execute()
    purchases = response.data

    tag_counts = {}
    for purchase in purchases:
        for product in purchase['products']:
            tag = product['TagClass']
            quantity = product.get('quantity', 1)  # Default to 1 if quantity is missing
            tag_counts[tag] = tag_counts.get(tag, 0) + quantity

    sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
    return [tag for tag, _ in sorted_tags]

# API to record user purchase (after payment)
@app.route('/purchase', methods=['POST'])
def record_purchase():
    data = request.json
    user_id = data['user_id']
    products = data['products']

    response = supabase.table('user_purchases').insert({
        'user_id': user_id,
        'products': products
    }).execute()

    if response.data:
        return jsonify({"message": "Purchase recorded successfully.", "status": "success", "code": 201, "user_id": user_id, "products": products}), 201
    else:
        return jsonify({"message": "Failed to record purchase", "status": "error", "code": 400}), 400

# API to get recommendations for a user
@app.route('/recommendations/<int:user_id>', methods=['GET'])
def get_recommendations(user_id):
    # Step 1: Get user's preferred tags
    user_tags = get_user_tags(user_id)
    if not user_tags:
        return jsonify({"message": "No recommendations available.", "status": "info", "code": 200}), 200

    # Step 2: Fetch all products
    products_response = invoke_http(PRODUCTS_API_URL, "GET")
    if 'code' in products_response and products_response['code'] != 200:
        return jsonify({"message": f"Error fetching products: {products_response.get('message', 'Unknown error')}", "status": "error", "code": 500}), 500

    all_products = products_response.get('Products', [])

    # Step 3: Fetch user's cart
    cart_response = invoke_http(CART_API_URL.format(user_id=user_id), "GET")
    if 'code' in cart_response and cart_response['code'] != 200:
        return jsonify({"message": f"Error fetching cart: {cart_response.get('message', 'Unknown error')}", "status": "error", "code": 500}), 500

    cart_items = cart_response.get('cart', {})
    cart_product_ids = {int(item.get("productId")) for item in cart_items.values()}

    # Step 4: Filter products based on user tags and exclude cart items
    recommendations = []

    for tag in user_tags:
        tag_products = [
            product for product in all_products
            if product['TagClass'] == tag and int(product['productId']) not in cart_product_ids
        ]
        random.shuffle(tag_products)
        recommendations.extend(tag_products)
        if len(recommendations) >= 3:
            break

    recommendations = recommendations[:3]  # Ensure no more than 3 are returned

    if not recommendations:
        return jsonify({"message": "No recommendations found for the user.", "status": "info", "code": 200}), 200

    return jsonify({"recommendations": recommendations, "status": "success", "code": 200}), 200



def callback(ch, method, properties, body):
    """Processes incoming AMQP messages and adds purchased products into table."""
    try:
        message = json.loads(body)

        # Extract necessary fields
        user_id = message.get("userID")
        products = message.get("products")

        if not user_id or not products:
            print("Invalid message format:", message)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        full_products = []
        for product in products:
            product_id = product.get("productId")
            quantity = product.get("stock")  # 'stock' represents quantity bought

            if not product_id or quantity is None:
                continue

            # Fetch full product details
            product_details = invoke_http(SINGLE_API_URL.format(productid=product_id), "GET")

            if not product_details.get("Result", {}).get("Success", False):
                continue

            product_info = product_details.get("Product", {})
            product_info["quantity"] = quantity  # Add quantity to product details
            full_products.append(product_info)

        if not full_products:
            print("No valid products retrieved. Skipping message.")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        # Construct payload for the /purchase endpoint
        purchase_data = {
            "user_id": user_id,
            "products": full_products
        }

        # Call the /purchase endpoint
        purchase_response = invoke_http("http://recommendation:5204/purchase", method="POST", json=purchase_data)

        # Log response
        print("Recommendation database logging response:", purchase_response)

        # Acknowledge the message after processing
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        print("Error processing message:", e)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)  # Reject and discard the message


def run_flask_app():
    app.run(host='0.0.0.0', port=5204, debug=False)


if __name__ == '__main__':
    # Start the Flask app in a separate thread so it does not block the RabbitMQ consumer
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.start()

    # Start the RabbitMQ consumer in the main thread
    rabbit.connect(RABBITMQ_HOST, RABBITMQ_PORT, PLACE_ORDER_EXCHANGE_NAME, "fanout", {RECOMMENDATION_QUEUE_NAME: ""})

    rabbit.start_consuming(RABBITMQ_HOST, RABBITMQ_PORT, PLACE_ORDER_EXCHANGE_NAME, "fanout", RECOMMENDATION_QUEUE_NAME, callback=callback)
