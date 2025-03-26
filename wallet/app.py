from flask import Flask, request, jsonify
from dotenv import load_dotenv
from utils import credit_wallet, debit_wallet, get_wallet_balance
import os

load_dotenv()
app = Flask(__name__)

@app.route('/wallet/credit', methods=['POST'])
def credit():
    data = request.get_json()
    user_id = data.get('user_id')
    points = data.get('points', 0)
    if not user_id or not isinstance(points, int):
        return jsonify({'error': 'Invalid input'}), 400
    new_balance = credit_wallet(user_id, points)
    return jsonify({'message': 'Points credited', 'balance': new_balance}), 200

@app.route('/wallet/debit', methods=['POST'])
def debit():
    data = request.get_json()
    user_id = data.get('user_id')
    points = data.get('points', 0)
    if not user_id or not isinstance(points, int):
        return jsonify({'error': 'Invalid input'}), 400
    new_balance = debit_wallet(user_id, points)
    if new_balance is None:
        return jsonify({'error': 'Insufficient points'}), 400
    return jsonify({'message': 'Points debited', 'balance': new_balance}), 200

@app.route('/wallet/balance/<user_id>', methods=['GET'])
def balance(user_id):
    balance = get_wallet_balance(user_id)
    return jsonify({'user_id': user_id, 'balance': balance}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5402)