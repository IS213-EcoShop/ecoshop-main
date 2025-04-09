from flask import Flask, request, jsonify
from dotenv import load_dotenv
from wallet_utils import credit_wallet, debit_wallet, get_wallet_balance, enable_cors, get_voucher_balance, delete_voucher_from_wallet
import os

import utils.amqp_lib as rabbit
import threading
import requests
import json
import pika

load_dotenv()
app = Flask(__name__)
enable_cors(app)

RABBITMQ_HOST = "rabbitmq"
RABBITMQ_PORT = 5672
PLACE_ORDER_EXCHANGE_NAME = "place_order_exchange"
WALLET_QUEUE_NAME = "wallet_queue"

@app.route('/wallet/credit', methods=['POST'])
def credit():
    data = request.get_json()
    user_id = data.get('user_id')
    points = data.get('points', 0)
    if not user_id or not isinstance(points, int):
        return jsonify({'error': 'Invalid input'}), 400
    result = credit_wallet(user_id, points)
    return jsonify({
        'message': 'Points credited',
        'balance': result['points'],
        'total_points': result['total_points']
    }), 200

@app.route('/wallet/debit', methods=['POST'])
def debit():
    data = request.get_json()
    user_id = data.get('user_id')
    points = data.get('points', 0)
    if not user_id or not isinstance(points, int):
        return jsonify({'error': 'Invalid input'}), 400
    result = debit_wallet(user_id, points)
    if result is None:
        return jsonify({'error': 'Insufficient points'}), 400
    return jsonify({
        'message': 'Points debited',
        'balance': result['poin ts'],
        'total_points': result['total_points']
    }), 200

@app.route('/wallet/balance/<user_id>', methods=['GET'])
def balance(user_id):
    result = get_wallet_balance(user_id)
    return jsonify({
        'user_id': user_id,
        'balance': result['points'],
        'total_points': result['total_points']
    }), 200

@app.route("/wallet/<user_id>", methods=["GET"])
def get_wallet(user_id):
    balance = get_wallet_balance(user_id)
    return jsonify(balance)

@app.route("/wallet/voucher/<user_id>", methods=["GET"])
def get_voucher(user_id):
    vouchers = get_voucher_balance(user_id)
    return jsonify(vouchers)

@app.route("/wallet/voucher/<user_id>/<voucher_id>", methods=["DELETE"])
def delete_voucher(user_id, voucher_id):
    result = delete_voucher_from_wallet(user_id, voucher_id)
    if result is None:
        return jsonify({'error': 'Voucher not found'}), 400
    return jsonify({'message': 'Voucher deleted successfully'}), 200

def callback(ch, method, properties, body):
    """Delete voucher upon receiving a message."""
    try:
        message = json.loads(body)
        print(f"Received message: {message}")

        voucher_info = message.get("voucher_info")
        if voucher_info and "voucherId" in voucher_info:
            user_id = message["user_details"]["profile"]["user_id"]  # Fix: Access user_id correctly
            voucher_id = voucher_info["voucherId"]
            
            print(f"Attempting to delete voucher {voucher_id} for user {user_id}")
            
            # Instead of making an HTTP request to itself, call the function directly
            result = delete_voucher_from_wallet(user_id, voucher_id)
            
            if result:
                print(f"Successfully deleted voucher {voucher_id} for user {user_id}")
            else:
                print(f"Failed to delete voucher {voucher_id} for user {user_id}")

    except Exception as e:
        print(f"Error processing message: {e}")
    finally:
        ch.basic_ack(delivery_tag=method.delivery_tag)

def run_flask_app():
    app.run(host='0.0.0.0', port=5402)

if __name__ == '__main__':
    # Connect to RabbitMQ and declare queue
    rabbit.connect(RABBITMQ_HOST, RABBITMQ_PORT, PLACE_ORDER_EXCHANGE_NAME, "fanout", {WALLET_QUEUE_NAME: ""})

    # Start the Flask app in a separate thread
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.start()

    # Start consuming messages
    rabbit.start_consuming(RABBITMQ_HOST, RABBITMQ_PORT, PLACE_ORDER_EXCHANGE_NAME, "fanout", WALLET_QUEUE_NAME, callback=callback)



# from flask import Flask, request, jsonify
# from dotenv import load_dotenv
# from utils import credit_wallet, debit_wallet, get_wallet_balance
# import os

# load_dotenv()
# app = Flask(__name__)

# @app.route('/wallet/credit', methods=['POST'])
# def credit():
#     data = request.get_json()
#     user_id = data.get('user_id')
#     points = data.get('points', 0)
#     if not user_id or not isinstance(points, int):
#         return jsonify({'error': 'Invalid input'}), 400
#     new_balance = credit_wallet(user_id, points)
#     return jsonify({'message': 'Points credited', 'balance': new_balance}), 200

# @app.route('/wallet/debit', methods=['POST'])
# def debit():
#     data = request.get_json()
#     user_id = data.get('user_id')
#     points = data.get('points', 0)
#     if not user_id or not isinstance(points, int):
#         return jsonify({'error': 'Invalid input'}), 400
#     new_balance = debit_wallet(user_id, points)
#     if new_balance is None:
#         return jsonify({'error': 'Insufficient points'}), 400
#     return jsonify({'message': 'Points debited', 'balance': new_balance}), 200

# @app.route('/wallet/balance/<user_id>', methods=['GET'])
# def balance(user_id):
#     balance = get_wallet_balance(user_id)
#     return jsonify({'user_id': user_id, 'balance': balance}), 200

# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=5402)


