import os
import sys
from flask import Flask, request, jsonify
import pika
import json
import threading
from utils.invokes import invoke_http
from utils.send_notif import notify_user
import utils.amqp_lib as rabbit
import utils.amqp_setup as setup

app = Flask(__name__)

# Microservice URLs
CART_SERVICE_URL = "http://cart:5201/cart"  # Cart service - Retrieve cart
PAYMENT_SERVICE_URL = "http://payment:5202/payment"  # Payment service

@app.route("/place_order", methods=['POST'])
def place_order():
    """ Handles the entire order process: Retrieve Cart --> Payment Creation """
    
    try:
        # Retrieve userID from the request
        user_id = request.json.get("userID")
        if not user_id:
            return jsonify({
                "code": 400,
                "message": "User ID is required."
            }), 400

        # Process the order through Cart and Payment Microservices
        result = processPlaceOrder(user_id)

        print("\n========== Notifying User ==========")

        notify_user(
            email="utkarshtayal90@gmail.com",
            message="order placed",
            data={"order_id":1},
            routing_key="email.order"
        )

        return jsonify(result), result["code"]
    
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        ex_str = str(e) + " at " + str(exc_type) + ": " + fname + ": line " + str(exc_tb.tb_lineno)
        print(ex_str)

        return jsonify({
            "code": 500,
            "message": "place_order.py internal error: " + ex_str
        }), 500

def processPlaceOrder(user_id):
    """ Retrieve cart and process the payment """

    print("\n========== Invoking cart microservice to retrieve the cart ==========")
    cart_result = invoke_http(f"{CART_SERVICE_URL}/{int(user_id)}", method='GET')

    if not cart_result or cart_result.get("code") != 200 or not cart_result.get("cart"):
        return {
            "code": 400,
            "message": "Failed to retrieve cart or cart is empty",
            "cart_result": cart_result
        }

    updated_cart = cart_result.get("cart")
    total_price = cart_result.get("total_price")

    payment_payload = {
        "userID": user_id,
        "amount": total_price,
        "currency": "SGD",
        "cart": updated_cart
    }

    print("\n========== Invoking the Payment Microservice ==========")
    payment_result = invoke_http(PAYMENT_SERVICE_URL, method='POST', json=payment_payload)

    if payment_result.get("paymentID"):
        return {
            "code": 201,
            "message": "Awaiting payment",
            "order_details": updated_cart,
            "payment_details": payment_result
        }
    else:
        return {
            "code": 500,
            "message": "Payment failed",
            "cart_result": cart_result,
            "payment_result": payment_result
        }
    

# RabbitMQ code

# AMQP Configuration
RABBITMQ_HOST = "rabbitmq"
RABBITMQ_PORT = 5672

# Exchange and Queue Names
EXCHANGE_NAME = "payment_exchange"
QUEUE_NAME = "payment_queue"
ROUTING_KEY = "payment_success"

ORDER_EXCHANGE_NAME = "order_topic"
CART_ROUTING_KEY = "order.clear"
PRODUCT_ROUTING_KEY = "order.reduce"

CART_SERVICE_URL = "http://cart-service/api/cart"  # Update with actual cart service URL


def callback(ch, method, properties, body):
    """Process messages from RabbitMQ."""
    message = json.loads(body)
    payment_id = message.get("paymentID")
    status = message.get("status")
    user_id = message.get("userID")

    print(f"Received message from {QUEUE_NAME}: {message}")

    if status == "successful":
        # Prepare message to clear cart
        cart_message = {"user_id": user_id, "action": "clear_cart"}

        # Retrieve cart details from the service
        cart_result = invoke_http(CART_SERVICE_URL, method="GET")
        if not cart_result or cart_result.get("code") != 200 or not cart_result.get("cart"):
            print("Failed to retrieve cart for reducing stock")
            return

        updated_cart = cart_result.get("cart")

        # Prepare product stock reduction message
        product_message = [
            {"productId": int(product["productId"]), "stock": int(product["quantity"])}
            for product in updated_cart.values()
        ]

        # Publish messages to cart and product services
        try:
            connection, channel = rabbit.connect(RABBITMQ_HOST, RABBITMQ_PORT, ORDER_EXCHANGE_NAME, "topic")

            # Publish message to clear the cart
            print(f"Publishing message to clear cart for user {user_id}")
            channel.basic_publish(
                exchange=ORDER_EXCHANGE_NAME,
                routing_key=CART_ROUTING_KEY,
                body=json.dumps(cart_message),
                properties=pika.BasicProperties(delivery_mode=2),
            )

            # Publish message to reduce stock
            print(f"Publishing message to reduce stock for products: {product_message}")
            channel.basic_publish(
                exchange=ORDER_EXCHANGE_NAME,
                routing_key=PRODUCT_ROUTING_KEY,
                body=json.dumps(product_message),
                properties=pika.BasicProperties(delivery_mode=2),
            )

            rabbit.close(connection, channel)
        except Exception as e:
            print(f"Error publishing messages: {e}")


def consume_payment_messages():
    """Start consuming messages from the payment queue."""
    rabbit.start_consuming(
        hostname=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        exchange_name=EXCHANGE_NAME,
        exchange_type="direct",
        queue_name=QUEUE_NAME,
        callback=callback,
    )

# Function to run the Flask app
def run_flask_app():
    app.run(host='0.0.0.0', port=5301)

if __name__ == '__main__':

    setup.setup_rabbitmq(
    hostname=RABBITMQ_HOST,
    port=RABBITMQ_PORT,
    exchange_name=ORDER_EXCHANGE_NAME,
    exchange_type="topic",
    queues={
        "payment_confirmation_queue": "payment.confirmation",
        "order_queue": "order.*",
        "payment_queue": "payment_success"
    })
    # Start the Flask app in a separate thread
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.start()

    # Start the RabbitMQ consumer in the main thread
    consume_payment_messages()
