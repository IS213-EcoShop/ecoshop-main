import pika
import json
import time
import requests
import logging
import os

# Simple logging configuration
logging.basicConfig(level=logging.INFO)

# EmailJS API details (replace with your actual credentials)
EMAILJS_USER_ID = os.getenv("EMAILJS_KEY")
EMAILJS_SERVICE_ID = os.getenv("EMAILJS_SERVICE_ID")
EMAILJS_TEMPLATE_ID = 'template_aqpb5ns'
EMAILJS_API_URL = "https://api.emailjs.com/api/v1.0/email/send"

RABBITMQ_HOST = 'rabbitmq'
NOTIF_EXCHANGE_NAME = 'notification_exchange'

def get_rabbitmq_connection():
    """
    Establishes a connection to RabbitMQ and returns the channel.
    """
    while True:
        try:
            logging.info("Trying to connect to RabbitMQ...")
            connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST))
            channel = connection.channel()
            logging.info("Connected to RabbitMQ")
            return channel
        except pika.exceptions.AMQPConnectionError:
            logging.warning("Connection failed, retrying in 5 seconds...")
            time.sleep(5)

def send_welcome_email(notification):
    """
    Sends an email via EmailJS API.
    """
    email, message, data = notification['email'], notification['message'], notification["data"]
    try:
        payload = {
            'service_id': EMAILJS_SERVICE_ID,
            'template_id': EMAILJS_TEMPLATE_ID,
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
    result = channel.queue_declare(queue='', exclusive=True)
    queue_name = result.method.queue

    # Binding queues to routing keys
    channel.queue_bind(exchange=NOTIF_EXCHANGE_NAME, queue=queue_name, routing_key='email.*')

    channel.basic_consume(
        queue=queue_name,
        on_message_callback=callback,
        auto_ack=False
    )
    logging.info("Waiting for messages with routing keys.")
    channel.start_consuming()

if __name__ == '__main__':
    start_consuming()
