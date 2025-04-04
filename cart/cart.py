import threading
import pika
import json
from flask import Flask, jsonify, request
from utils.supabase import get_supabase
import utils.amqp_lib as rabbit
import time
from utils.cors_config import enable_cors

supabase = get_supabase()

RABBITMQ_HOST = "rabbitmq"
RABBITMQ_PORT = 5672

CART_QUEUE_NAME = "cart_queue"
PLACE_ORDER_EXCHANGE_NAME = "place_order_exchange"

app = Flask(__name__)
enable_cors(app)

@app.route('/cart/add', methods=['POST'])
def add_to_cart():
    data = request.json
    product = data.get("product")
    quantity = data.get("quantity")
    user_id = data.get("user_id")
    product_id = product.get("productId")

    if not isinstance(product_id, int) or product_id <= 0:
        return jsonify({"code": 400, "error": "Invalid productId"}), 400
    if not isinstance(quantity, int) or quantity < 0:
        return jsonify({"code": 400, "error": "Quantity must be a positive integer"}), 400

    del product["Stock"]
    product["quantity"] = quantity

    try:
        response = supabase.table("carts").select("*").eq("user_id", user_id).execute()
        if not response.data:
            new_cart = {str(product_id): product}
            supabase.table("carts").insert({"user_id": user_id, "cart": new_cart}).execute()
            return jsonify({"code": 200, "message": "Cart created", "cart": new_cart}), 200
        else:
            existing_cart = response.data[0].get("cart", {})
            existing_product = existing_cart.get(str(product_id))

            if existing_product:
                product["quantity"] = existing_product.get("quantity", 0) + quantity

            existing_cart[str(product_id)] = product
            supabase.table("carts").update({"cart": existing_cart}).eq("user_id", user_id).execute()

            total_price = sum(item["quantity"] * item["Price"] for item in existing_cart.values())
            return jsonify({"code": 200, "message": "Cart updated", "cart": existing_cart, "total_price": total_price}), 200

    except Exception as e:
        return jsonify({"code": 500, "error": str(e)}), 500
    

@app.route('/cart/decrement', methods=['PUT'])
def decrement_quantity():
    """ Decrease quantity of a product in the cart by 1. Stop at 1, don't remove. """
    data = request.json
    product_id = data.get("productId")
    user_id = data.get("user_id")

    if not isinstance(product_id, int) or product_id <= 0:
        return jsonify({"code": 400, "error": "Invalid productId"}), 400

    try:
        response = supabase.table("carts").select("*").eq("user_id", user_id).execute()

        if not response.data:
            return jsonify({"code": 404, "error": "Cart not found"}), 404

        cart = response.data[0]["cart"]

        if str(product_id) not in cart:
            return jsonify({"code": 404, "error": "Product not found in cart"}), 404

        current_quantity = cart[str(product_id)]["quantity"]
        if current_quantity > 1:
            cart[str(product_id)]["quantity"] = current_quantity - 1
        else:
            return jsonify({"code": 400, "error": "Cannot decrement below 1"}), 400

        supabase.table("carts").update({"cart": cart}).eq("user_id", user_id).execute()

        total_price = sum(item["quantity"] * item["Price"] for item in cart.values())
        return jsonify({"code": 200, "message": "Quantity decremented", "cart": cart, "total_price": total_price}), 200

    except Exception as e:
        return jsonify({"code": 500, "error": str(e)}), 500


@app.route('/cart/remove', methods=['PUT']) # replacement function to remove the entire product from the listing
def decrement_cart():
    """ Decrease the quantity of a product in the cart or remove it. """
    print("=============REMOVE PRODUCT FROM CART==================")
    data = request.json
    product_id = data.get("productId")
    user_id = data.get("user_id")

    if not isinstance(product_id, int) or product_id <= 0:
        return jsonify({"code": 400, "error": "Invalid productId"}), 400

    try:
        response = (supabase.table("carts")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )
        cart = response.data[0]["cart"]
        print(cart)

        if str(product_id) not in cart:
            print(str(product_id), cart)
            return jsonify({"code": 404, "error": "Product not found in cart"}), 404
        
        del cart[str(product_id)]

        try:
            response = (
                supabase.table("carts")
                .update({"cart": cart})
                .eq("user_id", user_id)
                .execute()
            )

            return jsonify({"code": 200, "message": "Product removed successfully", "cart": cart, "response" : response.data}), 200
        except Exception as e:
            return {"error": "Couldn't update removed cart", "message": str(e)}, 404

    except Exception as e:
        return {"error" : "Couldn't get user's cart", "message":str(e)}, 500



@app.route('/cart/<user_id>', methods=['GET'])
def view_cart(user_id):
    """ Get all items in the cart and total price. """
    print("====== GETTING USER'S CART INFO ======")
    print(user_id)
    try:
        response = (
            supabase.table("carts")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )

        if not response.data:
            # No cart found for user — return empty cart
            return jsonify({"code": 200, "cart": {}, "total_price": 0}), 200

        cart_items = response.data[0]["cart"]
        total_price = sum(item["quantity"] * item["Price"] for item in cart_items.values())
        return jsonify({"code": 200, "cart": cart_items, "total_price": total_price}), 200

    except Exception as e:
        return {"error" : "Failed to retrieve cart", "message" : str(e)}, 500



@app.route('/cart/clear/<user_id>', methods=['DELETE'])
def clear_cart(user_id):
    """ Clear all items from cart after successful payment """
    try:
        clear_user_cart(user_id)
        return jsonify({"code": 200, "message": "Cart has been successfully cleared."})
    except Exception as e:
        return {"error" : "Could not delete user's cart", "message": str(e)}, 500
    
def clear_user_cart(user_id):
    """ Clear all items from cart in Supabase """
    try:
        response = (
            supabase.table("carts")
            .delete()
            .eq("user_id", user_id)
            .execute()
        )
        print(f"Cart cleared for user {user_id}.")
    except Exception as e:
        print(f"Error clearing cart for user {user_id}: {str(e)}")


# This function will process messages from RabbitMQ
def callback(ch, method, properties, body):
    try:
        message = json.loads(body)
        print(f"Received message: {message}")
        
        user_id = message.get('userID')

        print("Clearing the cart...")
        clear_user_cart(user_id)
        print("Cart has been cleared.")

    except Exception as e:
        print(f"Error processing message: {e}")
    finally:
        ch.basic_ack(delivery_tag=method.delivery_tag)


# Function to run the Flask app
def run_flask_app():
    app.run(host='0.0.0.0', port=5201)

if __name__ == '__main__':
    #REDUNDANCY 
    rabbit.connect(RABBITMQ_HOST, RABBITMQ_PORT, PLACE_ORDER_EXCHANGE_NAME, "fanout", {CART_QUEUE_NAME: ""})

    # Start the Flask app in a separate thread
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.start()

    # IS A CONSUMER
    rabbit.start_consuming(RABBITMQ_HOST, RABBITMQ_PORT, PLACE_ORDER_EXCHANGE_NAME, "fanout", CART_QUEUE_NAME, callback=callback)
