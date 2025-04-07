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
PLACE_ORDER_EXCHANGE_NAME = "place_order_exchange"
NOTIF_QUEUE_NAME = 'send_email_queue'

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

def send_order_email(body):
    """
    Sends an order confirmation email (currently a placeholder function).
    """
    print("===========================SENDING ORDER EMAIL=======================================")

    user_profile = body["user_details"]["profile"]
    cart = body["cart"]
    print("Extracted Relevant Information")
    # Build list of orders as HTML string to match the EmailJS template
    total = 0
    orders = []
    logging.info(cart)
    logging.info("cart body")
    for product_id, item in cart.items():
        product_name = item["Name"]
        product_quantity = item["quantity"]
        image_url = item["ImageURL"]
        price = item["Price"]
        total += price * product_quantity
        product_total = price * product_quantity
        orders += [{"product_name" : product_name,"product_quantity":product_quantity, "image_url":image_url,"price":product_total}]
    logging.info(f"Orders: {orders}")
    try:
        payload = {
            'service_id': EMAILJS_SERVICE_ID,
            'template_id': ORDER_EMAILJS_TEMPLATE_ID,
            'user_id': EMAILJS_USER_ID,
            "template_params": {
                "email": user_profile["email"],
                "name": user_profile["name"],
                "total": f"{total:.2f}",
                "orders": orders
            }
        }
        return {}, 200
        # response = requests.post(EMAILJS_API_URL, json=payload)

        # if response.status_code == 200:
        #     logging.info(f"Email sent successfully: {response.text}")
        #     return {"response": {response.text}}, 200
        # else:
        #     logging.error(f"Failed to send email. Response: {response.status_code} - {response.text}")
        #     return response.status_code
    except Exception as e:
        logging.error(f"Error while sending email: {e}")
        return {}, 404


def callback(ch, method, properties, body):
    """
    Callback function to process messages from RabbitMQ.
    """
    logging.info(f"Received message: {body} ================")

    try:
        body = json.loads(body)
        if body.get("message") == "complete transaction":
            send_order_email(body)  # pass the parsed dict
            pass
    except Exception as e:
        logging.error(f"Error processing message: {e}")
    finally:
        ch.basic_ack(delivery_tag=method.delivery_tag)

if __name__ == '__main__':
    # Start consuming messages

    rabbit.connect(RABBITMQ_HOST, RABBITMQ_PORT, PLACE_ORDER_EXCHANGE_NAME, "fanout", {NOTIF_QUEUE_NAME: ""})
    print("SEND_EMAIL INITIALISED")
    # IS A CONSUMER
    rabbit.start_consuming(RABBITMQ_HOST, RABBITMQ_PORT, PLACE_ORDER_EXCHANGE_NAME, "fanout", NOTIF_QUEUE_NAME, callback=callback)

    # send_email-1      | INFO:root:Received message: b'{"message": "complete transaction", "userID": 200, "products": [{"productId": 11, "stock": 2}]}' ================
    # rabbitmq          | 2025-04-07 05:42:06.712040+00:00 [info] <0.962.0> closing AMQP connection (172.18.0.10:51928 -> 172.18.0.2:5672, vhost: '/', user: 'guest', duration: '21ms')
    # send_email-1      | WARNING:root:Unhandled routing key: 

# {
#     "message": "complete transaction",
#     "userID": 200,
#     "products": [
#         {
#         "productId": 12,
#         "stock": 1
#         }
#     ],
#     "user_details": {
#         "profile": {
#         "address": "address",
#         "email": "utkarshtayal90@gmail.com",
#         "name": "utkarsh",
#         "password": "password",
#         "phone": "+6500000000",
#         "user_id": 200
#         }
#     },
#     "cart": {
#         "12": {
#         "Category": "Furniture",
#         "Condition": "New",
#         "Description": "Handcrafted from raw terracotta",
#         "ImageURL": "https://cvtknyvnrxhaqdvdmlde.supabase.co/storage/v1/object/public/product-images//terracotta.png",
#         "Name": "Terracotta Side Table",
#         "Price": 36.98,
#         "SustainabilityPoints": 17,
#         "TagClass": "plastic-free",
#         "productId": 12,
#         "quantity": 1
#         }
#     }
# }
