import threading
import pika
import json
from flask import Flask, request, jsonify
from utils.supabase import get_supabase
import utils.amqp_lib as rabbit
from utils.cors_config import enable_cors
from utils.invokes import invoke_http

supabase = get_supabase()

RABBITMQ_HOST = "rabbitmq"
RABBITMQ_PORT = 5672

DELIVERY_PLACE_ORDER_QUEUE_NAME = "delivery_place_order_queue"
PLACE_ORDER_EXCHANGE_NAME = "place_order_exchange"

VERIFICATION_EXCHANGE_NAME = "verification_exchange"
DELIVERY_VERIFICATION_QUEUE_NAME = "delivery_verification_queue"

USER_SERVICE_URL = "http://profile:5001/profile"

EXTERNAL_URL = "https://personal-slqn7xxm.outsystemscloud.com/ESDProject_VanNova_/rest/JohnnyAPI"

app = Flask(__name__)
enable_cors(app)

def do_order_delivery(body): #for orders
    user_details = body["user_details"]
    payment_id = body["payment_id"]

    try: #handle creation of order
        response = create_order(user_details)
        print("Order created")
    except Exception as e:
        error_message = f"Error while creating order: {str(e)}"
        return jsonify({"error": error_message}), 500 
    
    try:
        if not response:
            raise ValueError("Order creation failed, response is invalid.")
        
        print(response)
        print("Attempting to insert delivery to Supabase...")
        supabase.table("delivery").insert({"user_id": user_details["profile"]["user_id"], "payment_id": payment_id, "order_id":response["order"]["id"] }).execute()
        print("Delivery inserted successfully.")
        return jsonify({"code": 200, "message": "Delivery added"}), 200
    except Exception as e:
        error_message = f"Error while inserting delivery into database: {str(e)}"
        return jsonify({"code": 500, "error": str(e)}), 500

#create an order
def create_order(body):
    print(body)
    user_profile = body["profile"]

    headers = {
        "X-Api-Key": "G1T46tsdgdjl9fsKDd5zsvnwmdjosDmrufbs93susadLHDvjfhbnwtTRbsnucnrb",
        "X-User-Id": str(user_profile["user_id"]),
        "Content-Type": "application/json"
    }

    #Create the order object
    order = {
        "order": {
            "orderDetails": "Sustainamart Order",
            "fromAddressLine1": "81 Victoria Street",
            "fromAddressLine2": None,
            "fromZipCode": "188065",
            "toAddressLine1": user_profile["address"],
            "toAddressLine2": None,
            "toZipCode": "680456", #assume spliced from address
            "userId": "200"
            }
        }
    
    response  = invoke_http(f"{EXTERNAL_URL}/order", "POST", json=order, headers=headers)
    return response


def do_verified_delivery(body):
    user_id = body["user_id"]
    print(user_id)
    user_details = invoke_http(f"{USER_SERVICE_URL}/{int(user_id)}", method="GET")
    print(user_details)




# This function will process messages from RabbitMQ
def callback(ch, method, properties, body):
    try:
        body = json.loads(body)
        print(f"Received message: {body}, {body['message']}") #needs to be modified to fit necessary criteria

        if body["message"] == "complete transaction":
            with app.app_context():
                do_order_delivery(body)
        elif "trade" in body:
            with app.app_context():
                do_verified_delivery(body)
        else:
            print("Unknown message format")

    except Exception as e:
        print(f"Error processing message: {e}")
    finally:
        ch.basic_ack(delivery_tag=method.delivery_tag)


# Function to run the Flask app
def run_flask_app():
    app.run(host='0.0.0.0', port=5209)

if __name__ == '__main__':
    rabbit.connect(RABBITMQ_HOST, RABBITMQ_PORT, PLACE_ORDER_EXCHANGE_NAME, "fanout", {DELIVERY_PLACE_ORDER_QUEUE_NAME: ""})
    rabbit.connect(RABBITMQ_HOST, RABBITMQ_PORT, VERIFICATION_EXCHANGE_NAME, "direct", {DELIVERY_VERIFICATION_QUEUE_NAME: "send_verification"})

    # Start the Flask app in a separate thread
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.start()

    # IS A CONSUMER
    # Start consumers in separate threads
    def start_consuming_place_order():
        rabbit.start_consuming(RABBITMQ_HOST, RABBITMQ_PORT, PLACE_ORDER_EXCHANGE_NAME, "fanout", DELIVERY_PLACE_ORDER_QUEUE_NAME, callback=callback)

    def start_consuming_verification():
        rabbit.start_consuming(RABBITMQ_HOST, RABBITMQ_PORT, VERIFICATION_EXCHANGE_NAME, "direct", DELIVERY_VERIFICATION_QUEUE_NAME, callback=callback)

    # Start each consumer in its own thread
    threading.Thread(target=start_consuming_place_order).start()
    threading.Thread(target=start_consuming_verification).start()



# Expected return
# {
#   "message": "complete transaction",
#   "userID": 200,
#   "products": [
#     {
#       "productId": 12,
#       "stock": 1
#     }
#   ],
#   "user_details": {
#     "profile": {
#       "address": "address",
#       "email": "utkarshtayal90@gmail.com",
#       "name": "utkarsh",
#       "password": "password",
#       "phone": "+6500000000",
#       "user_id": 200
#     }
#   },
#   "cart": {
#     "12": {
#       "Category": "Furniture",
#       "Condition": "New",
#       "Description": "Handcrafted from raw terracotta",
#       "ImageURL": "https://cvtknyvnrxhaqdvdmlde.supabase.co/storage/v1/object/public/product-images//terracotta.png",
#       "Name": "Terracotta Side Table",
#       "Price": 36.98,
#       "SustainabilityPoints": 17,
#       "TagClass": "plastic-free",
#       "productId": 12,
#       "quantity": 1
#     }
#   }
# }


# {
#     'message': 'Trade Successful',
#     'user_id': 'user_id',
#     'trade': {
#         'id': 3,
#         'created_at': '2025-03-26T20:53:08.006205+00:00',
#         'user_id': 'coat_wearer',
#         'product_name': 'red_coat',
#         'image_url': 'https://cvtknyvnrxhaqdvdmlde.supabase.co/storage/v1/object/public/tradein-images/red_coat.jpeg?',
#         'status': 'accepted',
#         'condition': None
#     }
# }

# {
#     'message': 'Trade Unsuccessful',
#     'user_id': 'user_id',
#     'trade': {
#         'id': 33,
#         'created_at': '2025-04-08T07:31:37.752595+00:00',
#         'user_id': '200',
#         'product_name': 'shirt',
#         'image_url': 'https://cvtknyvnrxhaqdvdmlde.supabase.co/storage/v1/object/public/tradein-images/e7ced15a-415c-4809-8b56-750517c652e5_Screenshot_2025-04-05_at_6.09.25_PM.png?',
#         'status': 'rejected',
#         'condition': None
#     }
# }