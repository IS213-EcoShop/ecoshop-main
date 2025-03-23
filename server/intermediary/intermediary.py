import pika
import json
import requests
from flask import Flask
import threading
import logging

# RabbitMQ Connection Details
RABBITMQ_HOST = 'rabbitmq'  # Ensure this matches the service name in docker-compose.yml
EXCHANGE_NAME = "order_topic"  # Exchange used in place_order.py
QUEUE_NAME = "product_queue"   # Queue where stock reduction messages are sent
PRODUCT_ROUTING_KEY = "order.reduce"  # Routing key for stock reduction messages

# Product Microservice API
PRODUCT_SERVICE_URL = "https://personal-o2kymv2n.outsystemscloud.com/SustainaMart/rest/v1/reducestock/"

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reduce_stock(product_id, stock):
    """Calls the Product Microservice API to reduce stock."""
    payload = {"productId": product_id, "stock": stock}
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.patch(PRODUCT_SERVICE_URL, json=payload, headers=headers)
        response.raise_for_status()  # Will raise an HTTPError for bad responses
        logger.info(f"Stock reduced for product {product_id}. Response: {response.status_code} - {response.text}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error reducing stock for product {product_id}: {e}")

def callback(ch, method, properties, body):
    """Processes incoming AMQP messages and invokes stock reduction API."""
    try:
        message = json.loads(body)
        logger.info(f"Received stock reduction message: {message}")

        if isinstance(message, list):  # Message format: List of {"productId": X, "stock": Y}
            for item in message:
                product_id = item.get("productId")
                stock = item.get("stock")
                if product_id is not None and stock is not None:
                    reduce_stock(product_id, stock)
                else:
                    logger.error(f"Invalid stock message format: {item}")
        else:
            logger.error("Received unexpected message format:", message)

    except json.JSONDecodeError:
        logger.error(f"Failed to decode message: {body}")

def consume_product_messages():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
    channel = connection.channel()

    # Declare the exchange and queue for product stock reduction
    channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='topic', durable=True)
    channel.queue_declare(queue="product_queue", durable=True)
    channel.queue_bind(exchange=EXCHANGE_NAME, queue="product_queue", routing_key=PRODUCT_ROUTING_KEY)

    # Set up the consumer with the callback function
    channel.basic_consume(queue="product_queue", on_message_callback=callback, auto_ack=True)

    logger.info("Waiting for product stock reduction messages...")
    channel.start_consuming()

def run_flask_app():
    app.run(host='0.0.0.0', port=5203, debug=False)

if __name__ == '__main__':
    # Start the Flask app in a separate thread so it does not block the RabbitMQ consumer
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.start()

    # Start the RabbitMQ consumer in the main thread
    consume_product_messages()
