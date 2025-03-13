from flask import Flask, request, jsonify
from utils.invoke import invoke_http  # Import invoke_http utility

app = Flask(__name__)

# Mock external payment service URL (replace with Stripe later)
PAYMENT_API_URL = "https://mock-payment-service.com/api/payment"

# Process payment
@app.route('/payment/process', methods=['POST'])
def process_payment():
    data = request.json
    amount = data.get("amount")
    payment_method = data.get("paymentMethod")
    
    if not amount or not payment_method:
        return jsonify({"error": "Amount and payment method are required"}), 400

    # Send payment data to the mock payment service
    payment_data = {
        "amount": amount,
        "paymentMethod": payment_method
    }

    response = invoke_http(PAYMENT_API_URL, method="POST", json=payment_data)

    if response.get("code") != 200:
        return jsonify({"error": "Payment failed", "details": response}), 500

    return jsonify({"message": "Payment successful", "paymentStatus": response}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003, debug=True)
