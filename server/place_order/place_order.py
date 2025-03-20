import os
import sys
from flask import Flask, request, jsonify
from utils.invokes import invoke_http

app = Flask(__name__)

# Microservice URLs
CART_SERVICE_URL = "http://cart:5201/cart"  # Cart service - Retrieve cart
PAYMENT_SERVICE_URL = "http://payment:5202/payment"  # Payment service

@app.route("/place_order", methods=['POST'])
def place_order():
    """ Handles the entire order process: Retrieve Cart --> Payment Creation """
    
    try:
        # Retrieve Street Address and Postal Code from the request
        street_address = request.json.get("street_address")
        postal_code = request.json.get("postal_code")
        
        if not street_address or not postal_code:
            return jsonify({
                "code": 400,
                "message": "Street Address and Postal Code are required."
            }), 400

        # Process the order through Cart and Payment Microservices
        result = processPlaceOrder(street_address, postal_code)
        return jsonify(result), result["code"]
    
    except Exception as e:
        # Unexpected error in code
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        ex_str = str(e) + " at " + str(exc_type) + ": " + fname + ": line " + str(exc_tb.tb_lineno)
        print(ex_str)

        return jsonify({
            "code": 500,
            "message": "place_order.py internal error: " + ex_str
        }), 500

def processPlaceOrder(street_address, postal_code):
    """ Retrieve cart and process the payment """

    print("\n----- Invoking cart microservice to retrieve the cart -----")
    cart_result = invoke_http(CART_SERVICE_URL, method='GET')
    print("cart_result:", cart_result)

    # Ensure the cart service returns a valid response with code 200 and a non-empty cart
    if not cart_result or cart_result.get("code") != 200 or not cart_result.get("cart"):
        return {
            "code": 400,
            "message": "Failed to retrieve cart or cart is empty",
            "cart_result": cart_result
        }

    updated_cart = cart_result.get("cart")
    total_price = cart_result.get("total_price")

    print("\n----- Invoking the Payment Microservice -----")
    payment_payload = {
        "userID": cart_result.get("userID", 1),  # For now there is no authentication in place, so assume use userID as 1 for testing purposes
        "amount": total_price,
        "currency": "SGD",
        "cart": updated_cart,
        "street_address": street_address,
        "postal_code": postal_code
    }

    payment_result = invoke_http(PAYMENT_SERVICE_URL, method='POST', json=payment_payload)
    print("Payment result:", payment_result)

    # Check if the payment creation was successful
    if payment_result.get("paymentID"):
        return {
            "code": 201,
            "message": "Order placed successfully",
            "order_details": updated_cart,
            "payment_details": payment_result,
            "delivery_address": {
                "street_address": street_address,
                "postal_code": postal_code
            }
        }
    else:
        return {
            "code": 500,
            "message": "Payment failed",
            "cart_result": cart_result,
            "payment_result": payment_result
        }

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5301, debug=True)
