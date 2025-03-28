import pika
import json
import time
import requests
import logging
import os
# import utils.amqp_setup as setup

# Simple logging configuration
logging.basicConfig(level=logging.INFO)

# EmailJS API details 
EMAILJS_USER_ID = os.getenv("EMAILJS_KEY")
EMAILJS_SERVICE_ID = os.getenv("EMAILJS_SERVICE_ID")
WELCOME_EMAILJS_TEMPLATE_ID = 'template_aqpb5ns'
ORDER_EMAILJS_TEMPLATE_ID = "template_2ks6jo9"
EMAILJS_API_URL = "https://api.emailjs.com/api/v1.0/email/send"

# RabbitMQ connection details
RABBITMQ_HOST = 'rabbitmq'
RABBITMQ_PORT = '5672'
NOTIF_EXCHANGE_NAME = 'notification_exchange'

# Helper function to establish RabbitMQ connection
def get_rabbitmq_connection():
    """
    Establishes a connection to RabbitMQ and returns the channel.
    """
    while True:
        try:
            logging.info("Trying to connect to RabbitMQ...")
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST, port=int(RABBITMQ_PORT)))
            channel = connection.channel()
            logging.info("Connected to RabbitMQ")
            return channel
        except pika.exceptions.AMQPConnectionError:
            logging.warning("Connection failed, retrying in 5 seconds...")
            time.sleep(5)

def send_welcome_email(notification):
    """
    Sends a welcome email via the EmailJS API.
    """
    print("==============================SENDING WELCOME EMAIL===================================")
    email, message, data = notification['email'], notification['message'], notification["data"]
    try:
        payload = {
            'service_id': EMAILJS_SERVICE_ID,
            'template_id': WELCOME_EMAILJS_TEMPLATE_ID,
            'user_id': EMAILJS_USER_ID,
            'template_params': {
                'email': email,
                'name': data.get("name", "User"),
                'message': message
            }
        }

        response = requests.post(EMAILJS_API_URL, json=payload)

        if response.status_code == 200:
            logging.info(f"Email sent successfully: {response.text}")
        else:
            logging.error(f"Failed to send email. Response: {response.status_code} - {response.text}")
    except Exception as e:
        logging.error(f"Error while sending email: {e}")

def send_order_email(notification):
    """
    Sends an order confirmation email (currently a placeholder function).
    """
    print("===========================SENDING ORDER EMAIL=======================================")
    return {}, 200  # This should be implemented based on the order email template.


def callback(ch, method, properties, body):
    """
    Callback function to process messages from RabbitMQ.
    """
    logging.info(f"Received message: {body}")

    try:
        notification = json.loads(body)
        routing_key = method.routing_key

        if routing_key == "email.welcome":
            send_welcome_email(notification)
        elif routing_key == "email.order":
            send_order_email(notification)
        else:
            logging.warning(f"Unhandled routing key: {routing_key}")
    except Exception as e:
        logging.error(f"Error processing message: {e}")
    finally:
        ch.basic_ack(delivery_tag=method.delivery_tag)

def start_consuming():
    """
    Starts consuming messages from the notification queue with routing keys.
    """
    channel = get_rabbitmq_connection()
    channel.exchange_declare(exchange=NOTIF_EXCHANGE_NAME, exchange_type='topic', durable=True)
    result = channel.queue_declare(queue='notification_queue', durable=True)  # Use a persistent queue
    queue_name = result.method.queue

    # Binding queues to routing keys
    channel.queue_bind(exchange=NOTIF_EXCHANGE_NAME, queue=queue_name, routing_key='email.*')  # Binds all email-related messages

    channel.basic_consume(
        queue=queue_name,
        on_message_callback=callback,
        auto_ack=False
    )
    logging.info("Waiting for messages with routing keys.")
    channel.start_consuming()

if __name__ == '__main__':
    # Set up RabbitMQ exchange and queues
    # setup.setup_rabbitmq(
    #     hostname=RABBITMQ_HOST,
    #     port=RABBITMQ_PORT,
    #     exchange_name=NOTIF_EXCHANGE_NAME,
    #     exchange_type='topic',
    #     queues={'notification_queue': 'email.*'},  # Binds all email-related messages
    # )

    connection = None
    queues={'notification_queue': 'email.*'}
    try:
        logging.info(f"Connecting to RabbitMQ at {RABBITMQ_HOST}:{RABBITMQ_PORT}...")
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                port=RABBITMQ_PORT,
                heartbeat=300,
                blocked_connection_timeout=300,
            )
        )
        channel = connection.channel()

        # Declare the exchange
        logging.info(f"Declaring exchange: {NOTIF_EXCHANGE_NAME} (Type: 'topic')")
        channel.exchange_declare(exchange=NOTIF_EXCHANGE_NAME, exchange_type='topic', durable=True)

        # Declare and bind each queue
        for queue_name, routing_key in queues.items():
            logging.info(f"Declaring queue: {queue_name}")
            channel.queue_declare(queue=queue_name, durable=True)
            logging.info(f"Binding queue {queue_name} to exchange {NOTIF_EXCHANGE_NAME} with routing key {routing_key}")
            channel.queue_bind(exchange=NOTIF_EXCHANGE_NAME, queue=queue_name, routing_key=routing_key)

        logging.info("RabbitMQ setup completed successfully.")

    except Exception as e:
        logging.error(f"Error setting up RabbitMQ: {e}")

    finally:
        if connection:
            connection.close()
            logging.info("RabbitMQ connection closed.")

    # Start consuming messages
    start_consuming()
