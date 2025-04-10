import os
import sys
from flask import Flask, request, jsonify
import pika
import json
from utils.invokes import invoke_http
import utils.amqp_lib as rabbit
import threading
from utils.cors_config import enable_cors

app = Flask(__name__)
enable_cors(app)

# Microservice URLs
CART_SERVICE_URL = "http://cart:5201/cart"  # Cart service - Retrieve cart
PAYMENT_SERVICE_URL = "http://payment:5202/payment"  # Payment service
USER_SERVICE_URL = "http://profile:5001/profile"

# RabbitMQ code
RABBITMQ_HOST = "rabbitmq"
RABBITMQ_PORT = 5672

# Exchange and Queue Names
PAYMENT_EXCHANGE_NAME = "payment_exchange"
PAYMENT_QUEUE_NAME = "payment_queue"
PAYMENT_ROUTING_KEY = "payment_success"

PLACE_ORDER_EXCHANGE_NAME = "place_order_exchange"

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

        # Get voucher information if provided
        voucher_id = request.json.get("voucherId")
        voucher_value = request.json.get("voucherValue", 0)

        # Process the order through Cart and Payment Microservices
        result = processPlaceOrder(user_id, voucher_id, voucher_value)

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

def processPlaceOrder(user_id, voucher_id=None, voucher_value=0):
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

    # Apply voucher discount if provided
    if voucher_value and float(voucher_value) > 0:
        original_price = total_price
        # Ensure total price doesn't go below zero
        total_price = max(total_price - float(voucher_value), 0)
        print(f"\n========== Applying voucher discount: ${voucher_value} ==========")
        print(f"Original price: ${original_price}, Discounted price: ${total_price}")

    payment_payload = {
        "userID": user_id,
        "amount": total_price,
        "currency": "SGD",
        "cart": updated_cart
    }

    # Add voucher information to payment payload if provided
    if voucher_id:
        payment_payload["voucherId"] = voucher_id
        payment_payload["voucherValue"] = voucher_value
        payment_payload["originalAmount"] = cart_result.get("total_price")  # Store original amount for reference

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
    



def callback(ch, method, properties, body):
    """Process messages from RabbitMQ."""
    message = json.loads(body)
    payment_id = message.get("paymentID")
    status = message.get("status")
    user_id = message.get("userID")

    print(f"Received message from {PAYMENT_QUEUE_NAME}: {message}")
    print(f"Message contents: {json.dumps(message, indent=2)}")  # Add this line to debug

    if status == "successful":
        # Retrieve cart details from the service
        cart_result = invoke_http(f"{CART_SERVICE_URL}/{int(user_id)}", method="GET")
        if not cart_result or cart_result.get("code") != 200 or not cart_result.get("cart"):
            print("Failed to retrieve cart for reducing stock")
            return
        
        user_details = invoke_http(f"{USER_SERVICE_URL}/{int(user_id)}", method="GET")
        if not user_details:
            print("Failed to retrieve user details")
            return

        updated_cart = cart_result.get("cart")
        
        product_message = [
            {"productId": int(product["productId"]), "stock": int(product["quantity"])}
            for product in updated_cart.values()
            ]
        try:
            # Publish fanout message
            print(f"Publishing message to fanout for user {user_id}")
            connection, channel = rabbit.connect(RABBITMQ_HOST, RABBITMQ_PORT, PLACE_ORDER_EXCHANGE_NAME, "fanout")

            # Include voucher information in the message if it was in the original payment
            voucher_info = {}
            
            # Check for voucher information in the message
            if "voucherId" in message:
                print(f"Found voucher info in message: voucherId={message.get('voucherId')}")
                voucher_info = {
                    "voucherId": message.get("voucherId"),
                    "voucherValue": message.get("voucherValue"),
                    "originalAmount": message.get("originalAmount")
                }
                print(f"Prepared voucher_info: {voucher_info}")
            
            # Create the message payload
            payload = {
                "message": "complete transaction", 
                "payment_id": payment_id, 
                "products": product_message, 
                "user_details": user_details, 
                "cart": updated_cart,
                "voucher_info": voucher_info
            }
            
            print(f"Publishing message with payload: {json.dumps(payload, indent=2)}")
            
            rabbit.publish_message(
                channel, 
                PLACE_ORDER_EXCHANGE_NAME,
                "", 
                payload
            )

            rabbit.close(connection, channel)
            print("======= Fanout Message Published =======")
        except Exception as e:
            print(f"Error publishing messages: {e}")
        finally:
            ch.basic_ack(delivery_tag=method.delivery_tag)


def run_flask_app():
    app.run(host='0.0.0.0', port=5301)

if __name__ == '__main__':

    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.start()

    rabbit.connect(RABBITMQ_HOST, RABBITMQ_PORT, PLACE_ORDER_EXCHANGE_NAME, "fanout") #create fanout queue

    #is redundancy 
    rabbit.connect(RABBITMQ_HOST,RABBITMQ_PORT,PAYMENT_EXCHANGE_NAME,"topic",{PAYMENT_QUEUE_NAME:PAYMENT_ROUTING_KEY})

    rabbit.start_consuming(RABBITMQ_HOST, RABBITMQ_PORT, PAYMENT_EXCHANGE_NAME,"topic",PAYMENT_QUEUE_NAME, callback=callback)