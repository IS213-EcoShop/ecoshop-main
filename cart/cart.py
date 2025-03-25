import threading
import pika
import json
from flask import Flask, jsonify, request

app = Flask(__name__)

# In-memory cart storage
cart = {}

ORDER_EXCHANGE_NAME = "order_topic"
CART_BINDING_KEY = "order.clear"

@app.route('/cart/add', methods=['POST'])
def add_to_cart():
    """ Add a product to the cart or update quantity. """
    data = request.json
    product_id = data.get("productId")
    quantity = data.get("quantity")
    product_name = data.get("productName")
    price = data.get("price")
    image_url = data.get("image_url")

    if not isinstance(product_id, int) or product_id <= 0:
        return jsonify({"code": 400, "error": "Invalid productId"}), 400

    if not isinstance(quantity, int) or quantity <= 0:
        return jsonify({"code": 400, "error": "Quantity must be a positive integer"}), 400

    # If product already exists in cart, update quantity
    if product_id in cart:
        cart[product_id]["quantity"] += quantity
    else:
        # Add new product to cart
        cart[product_id] = {
            "productId": product_id,
            "name": product_name,
            "price": price,
            "quantity": quantity,
            "image_url": image_url
        }

    total_price = sum(item["quantity"] * item["price"] for item in cart.values())
    return jsonify({"code": 200, "message": "Cart updated successfully", "cart": cart, "total_price": total_price}), 200

@app.route('/cart/decrement', methods=['POST'])
def decrement_cart():
    """ Decrease the quantity of a product in the cart or remove it. """
    data = request.json
    product_id = data.get("productId")
    quantity = data.get("quantity")

    if not isinstance(product_id, int) or product_id <= 0:
        return jsonify({"code": 400, "error": "Invalid productId"}), 400

    if not isinstance(quantity, int) or quantity <= 0:
        return jsonify({"code": 400, "error": "Quantity must be a positive integer"}), 400

    if product_id not in cart:
        return jsonify({"code": 404, "error": "Product not found in cart"}), 404

    # Decrease quantity or remove product if quantity goes to zero or below
    if cart[product_id]["quantity"] > quantity:
        cart[product_id]["quantity"] -= quantity
    else:
        del cart[product_id]

    total_price = sum(item["quantity"] * item["price"] for item in cart.values())
    return jsonify({"code": 200, "message": "Cart updated successfully", "cart": cart, "total_price": total_price}), 200

@app.route('/cart', methods=['GET'])
def view_cart():
    """ Get all items in the cart and total price. """
    total_price = sum(item["quantity"] * item["price"] for item in cart.values())
    return jsonify({"code": 200, "cart": cart, "total_price": total_price}), 200

@app.route('/cart/clear', methods=['DELETE'])
def clear_cart():
    """ Clear all items from cart after successful payment """
    cart.clear()
    return jsonify({"code": 200, "message": "Cart has been successfully cleared."})

# This function will process messages from RabbitMQ
def callback(ch, method, properties, body):
    try:
        message = json.loads(body)
        print(f"Received message: {message}")
        
        if isinstance(message, list):
            print("Message is a list. Processing first item.")
            message = message[0]  # Process the first item in the list

        action = message.get('action')
        
        if action == "clear_cart":
            # Clear the cart
            print("Clearing the cart...")
            cart.clear()
            print("Cart has been cleared.")
        else:
            print(f"Unknown action: {action}")
    except Exception as e:
        print(f"Error processing message: {e}")


# Start consuming messages from RabbitMQ
def consume_order_messages():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
    channel = connection.channel()

    # Declare the exchange and queue to ensure they're created
    channel.exchange_declare(exchange=ORDER_EXCHANGE_NAME, exchange_type='topic', durable=True)
    channel.queue_declare(queue="cart_queue", durable=True)
    channel.queue_bind(exchange=ORDER_EXCHANGE_NAME, queue="cart_queue", routing_key=CART_BINDING_KEY)

    # Set up the consumer with the callback function
    channel.basic_consume(queue="cart_queue", on_message_callback=callback, auto_ack=True)

    print("Waiting for messages from RabbitMQ...")
    channel.start_consuming()

# Function to run the Flask app
def run_flask_app():
    app.run(host='0.0.0.0', port=5201)

if __name__ == '__main__':
    # Start the Flask app in a separate thread
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.start()

    # Start the RabbitMQ consumer in the main thread
    consume_order_messages()
