import os
import sys
from flask import Flask, request, jsonify
from utils.invokes import invoke_http
from utils.cors_config import enable_cors

app = Flask(__name__)
enable_cors(app)

# Microservice URLs
PRODUCT_SERVICE_URL = "https://personal-o2kymv2n.outsystemscloud.com/SustainaMart/rest/v1/products/{}"
CART_SERVICE_URL = "http://cart:5201/cart"

@app.route("/cart-product/add", methods=['POST'])
def add_to_cart():
    """ Handles adding an item to the cart (increment behavior) """
    try:
        data = request.json
        userID = data.get("userID")
        product_id = data.get("productId")
        quantity = data.get("quantity", 1)  # Default to 1 if not provided

        if not isinstance(product_id, int) or product_id <= 0:
            return jsonify({"code": 400, "error": "Invalid productId"}), 400
        
        if not isinstance(quantity, int) or quantity <= 0:
            return jsonify({"code": 400, "error": "Quantity must be a positive integer"}), 400

        # Step 1: Get user's current cart to determine existing quantity
        cart_response = invoke_http(f"{CART_SERVICE_URL}/{userID}", method="GET")
        if "error" in cart_response:
            current_quantity = 0
        else:
            current_quantity = cart_response.get("cart", {}).get(str(product_id), {}).get("quantity", 0)

        # Step 2: Fetch product details from Product Microservice
        product_response = invoke_http(PRODUCT_SERVICE_URL.format(product_id), method="GET")

        print(f"Product API Response: {product_response}")  

        if not product_response or not product_response.get("Result", {}).get("Success"):
            return jsonify({"code": 404, "error": "Product not found"}), 404

        product = product_response.get("Product")
        if not product:
            return jsonify({"code": 404, "error": "Product data not found"}), 404

        stock = product.get("Stock")
        new_quantity = current_quantity + quantity

        if new_quantity > stock:
            return jsonify({
                "code": 400,
                "error": f"Not enough stock. Current in cart: {current_quantity}, Available: {stock - current_quantity}"
            }), 400

        # Step 3: Prepare payload for cart microservice
        product["quantity"] = new_quantity  # Full updated quantity
        cart_payload = {
            "product": product,
            "quantity": quantity,  # Only the increment to be added
            "user_id": userID
        }

        # Step 4: Forward to Cart Microservice
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
    

@app.route("/cart-product/decrement", methods=['POST'])
def decrement_cart_product():
    """ Handles decrementing quantity of an item in the cart """
    try:
        data = request.json
        user_id = data.get("userID")
        product_id = data.get("productId")

        if not isinstance(product_id, int) or product_id <= 0:
            return jsonify({"code": 400, "error": "Invalid productId"}), 400

        # Step 1: Check if the product exists in the user's cart
        cart_response = invoke_http(f"{CART_SERVICE_URL}/{user_id}", method="GET")

        if not cart_response or "cart" not in cart_response:
            return jsonify({"code": 404, "error": "Cart not found"}), 404

        if str(product_id) not in cart_response["cart"]:
            return jsonify({"code": 404, "error": "Product not found in cart"}), 404

        # Step 2: Send decrement request to cart service
        decrement_payload = {
            "productId": product_id,
            "user_id": user_id
        }
        response = invoke_http(f"{CART_SERVICE_URL}/decrement", method="PUT", json=decrement_payload)
        return jsonify(response), response.get("code", 500)

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
        user_id = data.get("userID")

        if not isinstance(product_id, int) or product_id <= 0:
            return jsonify({"code": 400, "error": "Invalid productId"}), 400

        # Forward the request to Cart Microservice
        cart_response = invoke_http(f"{CART_SERVICE_URL}/remove", method="PUT", json={"productId": product_id, "user_id": user_id})
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
