import logging
from flask import Flask, request, jsonify
from ..utils.invokes import invoke_http
from flasgger import Swagger

app = Flask(__name__)
swagger = Swagger(app)  # Initialize Swagger with Flask app

# External product API URL
PRODUCT_API_URL = "https://personal-o2kymv2n.outsystemscloud.com/SustainaMart/rest/v1/products/{}/"

# In-memory cart storage
cart = {}

def get_product_by_id(product_id):
    """
    Helper function to fetch product details by product ID.
    """
    url = PRODUCT_API_URL.format(product_id)
    product_data = invoke_http(url, method="GET")

    # Log the response from the external product API
    logging.debug(f"Response from product API for ID {product_id}: {product_data}")

    if not product_data or product_data.get("Result", {}).get("Success") is not True:
        logging.error(f"Failed to fetch product details for ID {product_id}.")
        return None

    # Extract product data from the correct location in the response
    product = product_data.get("Product", None)

    if product:
        logging.debug(f"Found Product: {product}")
    else:
        logging.debug(f"No product found with ID: {product_id}")
    
    return product


@app.route('/cart/update', methods=['POST'])
def update():
    """
    update product quantity in the cart.
    """
    data = request.json
    product_id = data.get("productId")
    quantity = data.get("quantity")

    # Validate that productId and quantity are valid
    if not isinstance(product_id, int) or product_id <= 0:
        return jsonify({"code":400, "error": "Invalid productId. Must be a positive integer."}), 400
    
    if not isinstance(quantity, int) or quantity <= 0:
        return jsonify({"code":400, "error": "Quantity must be a valid positive integer."}), 400

    # Log the received productId and quantity
    logging.debug(f"Received productId: {product_id}, quantity: {quantity}")

    # Fetch product details using helper function
    product = get_product_by_id(product_id)

    if not product:
        return jsonify({"code": 400, "error": "Invalid product ID"}), 400

    product_price = product["Price"]
    product_stock = product["Stock"]

    # Check if the requested quantity is available in stock
    if quantity > product_stock:
        return jsonify({"code": 400, "error": f"Not enough stock. Available: {product_stock}."}), 400

    # If the product already exists in the cart, update the quantity
    if product_id in cart:
        cart[product_id]["quantity"] = quantity
    else:
        # If the product doesn't exist in the cart, add it
        cart[product_id] = {
            "productId": product_id,
            "name": product["Name"],
            "price": product_price,
            "quantity": quantity,
            "image_url": product["Image"]
        }

    total_price = sum(item["quantity"] * item["price"] for item in cart.values())
    return jsonify({"code": 200, "message": "Cart updated successfully", "cart": cart, "total_price": total_price}), 200


@app.route('/cart/remove', methods=['DELETE'])
def remove_from_cart():
    """
    Remove product from cart.
    """
    data = request.json
    product_id = data.get("productId")

    if not isinstance(product_id, int) or product_id <= 0:
        return jsonify({"code": 400, "error": "Invalid productId. Must be a positive integer."}), 400

    if product_id in cart:
        del cart[product_id]
        return jsonify({"code": 200, "message": "Product removed from cart", "cart": cart}), 200
    else:
        return jsonify({"code": 404, "error": "Product not found in cart"}), 404


@app.route('/cart', methods=['GET'])
def view_cart():
    """
    Get all items in the cart and total price.
    """
    if not cart:  # If the cart is empty, return an empty cart
        return jsonify({"code": 200, "cart": {}, "total_price": 0.0}), 200

    total_price = sum(item["quantity"] * item["price"] for item in cart.values())
    return jsonify({"code": 200, "cart": cart, "total_price": total_price}), 200


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)  # Enable logging at debug level
    app.run(host='0.0.0.0', port=5201, debug=True)

