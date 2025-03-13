from flask import Flask, request, jsonify
from utils.invoke import invoke_http  # Import invoke_http utility

app = Flask(__name__)

# Microservice URLs
CART_SERVICE_URL = "http://localhost:5002/cart/total"  # Cart service
PAYMENT_SERVICE_URL = "http://localhost:5003/payment/process"  # Payment service
ORDER_SERVICE_URL = "http://localhost:5004/order/create"  # Order service

# Complete order process
@app.route('/order/complete', methods=['POST'])
def complete_order():
    data = request.json
    user_id = data.get("userID")
    
    if not user_id:
        return jsonify({"error": "User ID is required"}), 400

    # Step 1: Get cart details
    cart_response = invoke_http(CART_SERVICE_URL, method="GET")
    if cart_response.get("code") != 200:
        return jsonify({"error": "Failed to fetch cart details"}), 500

    cart = cart_response.get("cart")
    total_price = cart_response.get("total_price")

    # Step 2: Process payment
    payment_data = {
        "amount": total_price,
        "paymentMethod": data.get("paymentMethod")
    }
    
    payment_response = invoke_http(PAYMENT_SERVICE_URL, method="POST", json=payment_data)
    if payment_response.get("code") != 200 or payment_response.get("message") != "Payment successful":
        return jsonify({"error": "Payment failed"}), 500

    # Step 3: Create the order
    order_data = {
        "cart": cart,
        "paymentStatus": "success"
    }
    
    order_response = invoke_http(ORDER_SERVICE_URL, method="POST", json=order_data)
    if order_response.get("code") != 200:
        return jsonify({"error": "Order creation failed"}), 500

    return jsonify({"message": "Order completed successfully", "order": order_response}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5005, debug=True)
