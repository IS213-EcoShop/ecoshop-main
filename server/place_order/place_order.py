import os
import sys
from flask import Flask, request, jsonify
import pika
import json
import threading
from utils.invokes import invoke_http

app = Flask(__name__)

# Microservice URLs
CART_SERVICE_URL = "http://cart:5201/cart"  # Cart service - Retrieve cart
PAYMENT_SERVICE_URL = "http://payment:5202/payment"  # Payment service

# Initialize AMQP variables for consumption from payment.py
EXCHANGE_NAME = "payment_exchange" 
QUEUE_NAME = "payment_queue"
ROUTING_KEY = "payment_success"

# Initialize AMQP variables for publishing to cart
ORDER_EXCHANGE_NAME = "order_topic"

# Initialize Routing Keys
CART_ROUTING_KEY = "order.clear"
PRODUCT_ROUTING_KEY = "order.reduce"

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
    cart_result = invoke_http(CART_SERVICE_URL, method='GET')

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

# This function will be used to process messages from RabbitMQ
def callback(ch, method, properties, body):
    message = json.loads(body)
    payment_id = message.get('paymentID')
    status = message.get('status')
    user_id = message.get('userID')

    print(f"Received message from {QUEUE_NAME}: {message}")

    if status == "successful":
        # Prepare message to be sent to cart service
        cart_message = {
            "userID": user_id,
            "action": "clear_cart"
        }

        # Establishing connection to AMQP to publish messages to cart,product,email,delivery (topic)
        connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
        channel = connection.channel()

        # Declare the exchange (ensure it exists)
        channel.exchange_declare(exchange=ORDER_EXCHANGE_NAME, exchange_type='topic', durable=True)

        # Declare the cart queue and bind it to the exchange 
        channel.queue_declare(queue="cart_queue", durable=True)
        channel.queue_bind(exchange=ORDER_EXCHANGE_NAME, queue="cart_queue", routing_key=CART_ROUTING_KEY)

        print(f"Publishing message to clear cart for user {user_id}")
        # Send the message to the queue
        channel.basic_publish(
            exchange=ORDER_EXCHANGE_NAME,
            routing_key=CART_ROUTING_KEY,
            body=json.dumps(cart_message),
            properties=pika.BasicProperties(
                delivery_mode=2 
            )
        )

        connection.close()

# Start consuming messages from RabbitMQ
def consume_payment_messages():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
    channel = connection.channel()

    # Declare the exchange (ensure it exists)
    channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='direct')

    # Declare and bind the queue to the exchange with the routing key
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    channel.queue_bind(exchange=EXCHANGE_NAME, queue=QUEUE_NAME, routing_key=ROUTING_KEY)

    # Set up the consumer with the callback function
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback, auto_ack=True)

    print(f"Waiting for messages from '{EXCHANGE_NAME}' with routing key '{ROUTING_KEY}'...")
    channel.start_consuming()

# Function to run the Flask app
def run_flask_app():
    app.run(host='0.0.0.0', port=5301)

if __name__ == '__main__':
    # Start the Flask app in a separate thread
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.start()

    # Start the RabbitMQ consumer in the main thread
    consume_payment_messages()
