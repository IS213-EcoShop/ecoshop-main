import pika
import json
import requests
from flask import Flask
import threading
import logging
import utils.amqp_lib as rabbit

# RabbitMQ Connection Details
RABBITMQ_HOST = 'rabbitmq'  
RABBITMQ_PORT = 5672
PRODUCT_QUEUE_NAME = "product_queue"   
PLACE_ORDER_EXCHANGE_NAME = "place_order_exchange"

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
        body = json.loads(body)
        message = body.get("products")
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
    finally:
        ch.basic_ack(delivery_tag=method.delivery_tag)
        


def run_flask_app():
    app.run(host='0.0.0.0', port=5203, debug=False)

if __name__ == '__main__':
    # Start the Flask app in a separate thread so it does not block the RabbitMQ consumer
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.start()

    # Start the RabbitMQ consumer in the main thread
    rabbit.connect(RABBITMQ_HOST, RABBITMQ_PORT, PLACE_ORDER_EXCHANGE_NAME, "fanout", {PRODUCT_QUEUE_NAME: ""})

    rabbit.start_consuming(RABBITMQ_HOST, RABBITMQ_PORT, PLACE_ORDER_EXCHANGE_NAME, "fanout", PRODUCT_QUEUE_NAME, callback=callback)
