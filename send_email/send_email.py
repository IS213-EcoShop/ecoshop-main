import pika
import json
import time
import requests
import logging
import os
import utils.amqp_lib as rabbit

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
RABBITMQ_PORT = 5672
NOTIF_EXCHANGE_NAME = 'notification_exchange'

def send_welcome_email(body):
    """
    Sends a welcome email via the EmailJS API.
    """
    print("==============================SENDING WELCOME EMAIL===================================")
    try:
        payload = {
            'service_id': EMAILJS_SERVICE_ID,
            'template_id': WELCOME_EMAILJS_TEMPLATE_ID,
            'user_id': EMAILJS_USER_ID,
            'template_params': {
                'email': body["email"],
                'name': body["name"]
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
    logging.info(f"Received message: {body} ================")

    try:
        body = json.loads(body)
        routing_key = method.routing_key

        if routing_key == "email.welcome":
            send_welcome_email(body)
        elif routing_key == "email.order":
            send_order_email(body)
        else:
            logging.warning(f"Unhandled routing key: {routing_key}")
    except Exception as e:
        logging.error(f"Error processing message: {e}")
    finally:
        ch.basic_ack(delivery_tag=method.delivery_tag)

if __name__ == '__main__':
    # Start consuming messages
    NOTIF_QUEUES = {"notification_queue" : "email.*"}

    rabbit.start_consuming(
        RABBITMQ_HOST, 
        RABBITMQ_PORT, 
        NOTIF_EXCHANGE_NAME, 
        "topic",
        "notification_queue",
        callback=callback
    )
