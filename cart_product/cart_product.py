import os
import sys
from flask import Flask, request, jsonify
from utils.invokes import invoke_http

app = Flask(__name__)

# Microservice URLs
PRODUCT_SERVICE_URL = "https://personal-o2kymv2n.outsystemscloud.com/SustainaMart/rest/v1/products/{}"
CART_SERVICE_URL = "http://cart:5201/cart"

@app.route("/cart-product/add", methods=['POST'])
def add_to_cart():
    """ Handles adding an item to the cart """
    try:
        data = request.json
        userID = data.get("userID")
        product_id = data.get("productId")
        quantity = data.get("quantity")

        if not isinstance(product_id, int) or product_id <= 0:
            return jsonify({"code": 400, "error": "Invalid productId"}), 400
        
        if not isinstance(quantity, int) or quantity < 0:
            return jsonify({"code": 400, "error": "Quantity must be a positive integer"}), 400

        # Fetch product details from Product Microservice
        product_response = invoke_http(PRODUCT_SERVICE_URL.format(product_id), method="GET")

        print(f"Product API Response: {product_response}")  

        if not product_response or not product_response.get("Result", {}).get("Success"):
            return jsonify({"code": 404, "error": "Product not found"}), 404


        # Extract the product data from the response
        product = product_response.get("Product")

        if not product:
            return jsonify({"code": 404, "error": "Product data not found"}), 404

        product_name = product.get("Name")
        price = product.get("Price")
        image_url = product.get("ImageURL")
        stock = product.get("Stock")

        if quantity > stock:
            return jsonify({"code": 400, "error": f"Not enough stock. Available: {stock}"}), 400

        # Forward the request to Cart Microservice
        cart_payload = {
            "productId": product_id,
            "quantity": quantity,
            "productName": product_name,
            "price": price,
            "image_url": image_url,
            "user_id": userID
        }

        cart_response = invoke_http(f"{CART_SERVICE_URL}/add", method="POST", json=cart_payload)
        print("==============ADDED TO CART==============")
        return jsonify(cart_response), cart_response.get("code", 500)

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        error_message = f"{str(e)} at {exc_type}: {fname}: line {exc_tb.tb_lineno}"
        print(error_message)

        return jsonify({
            "code": 500,
            "message": "Internal error in cart-product service",
            "error": error_message
        }), 500



@app.route("/cart-product/remove", methods=['POST'])
def remove_from_cart():
    """ Handles full removal of an item from the cart. """
    try:
        data = request.json
        product_id = data.get("productId")
        user_id = data.get("user_id")

        if not isinstance(product_id, int) or product_id <= 0:
            return jsonify({"code": 400, "error": "Invalid productId"}), 400

        # Forward the request to Cart Microservice
        cart_response = invoke_http(f"{CART_SERVICE_URL}/remove", method="PUT", json={"productId": product_id, "user_id" :user_id})
        return jsonify(cart_response), cart_response.get("code", 500)

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        error_message = f"{str(e)} at {exc_type}: {fname}: line {exc_tb.tb_lineno}"
        print(error_message)

        return jsonify({
            "code": 500,
            "message": "Internal error in cart-product service",
            "error": error_message
        }), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5300, debug=True)
