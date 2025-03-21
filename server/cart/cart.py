import logging
from flask import Flask, request, jsonify
from flasgger import Swagger

app = Flask(__name__)
swagger = Swagger(app)  # Initialize Swagger with Flask app

# In-memory cart storage
cart = {}

@app.route('/cart/add', methods=['POST'])
def add_to_cart():
    """
    Add a product to the cart or update quantity.
    """
    data = request.json
    product_id = data.get("productId")
    quantity = data.get("quantity")
    product_name = data.get("productName")
    price = data.get("price")
    image_url = data.get("image_url")

    if not isinstance(product_id, int) or product_id <= 0:
        return jsonify({"code": 400, "error": "Invalid productId"}), 400

    if not isinstance(quantity, int) or quantity <= 0:
        return jsonify({"code": 400, "error": "Quantity must be a positive integer"}), 400

    # If product already exists in cart, update quantity
    if product_id in cart:
        cart[product_id]["quantity"] += quantity
    else:
        # Add new product to cart
        cart[product_id] = {
            "productId": product_id,
            "name": product_name,
            "price": price,
            "quantity": quantity,
            "image_url": image_url
        }

    total_price = sum(item["quantity"] * item["price"] for item in cart.values())
    return jsonify({"code": 200, "message": "Cart updated successfully", "cart": cart, "total_price": total_price}), 200


@app.route('/cart/decrement', methods=['POST'])
def decrement_quantity():
    """
    Decrease product quantity in the cart by a given amount. 
    If quantity reaches 0, remove the product.
    """
    data = request.json
    product_id = data.get("productId")
    quantity = data.get("quantity")  # Allow decrementing by a specified amount

    if not isinstance(product_id, int) or product_id <= 0:
        return jsonify({"code": 400, "error": "Invalid productId"}), 400

    if not isinstance(quantity, int) or quantity <= 0:
        return jsonify({"code": 400, "error": "Quantity must be a positive integer"}), 400

    if product_id in cart:
        if cart[product_id]["quantity"] > quantity:
            cart[product_id]["quantity"] -= quantity
        else:
            del cart[product_id]  # Remove product if quantity reaches 0
        
        total_price = sum(item["quantity"] * item["price"] for item in cart.values())
        return jsonify({"code": 200, "message": "Product quantity decreased", "cart": cart, "total_price": total_price}), 200
    else:
        return jsonify({"code": 404, "error": "Product not found in cart"}), 404



@app.route('/cart/remove', methods=['DELETE'])
def remove_from_cart():
    """
    Remove product from cart completely.
    """
    data = request.json
    product_id = data.get("productId")

    if not isinstance(product_id, int) or product_id <= 0:
        return jsonify({"code": 400, "error": "Invalid productId"}), 400

    if product_id in cart:
        del cart[product_id]
        total_price = sum(item["quantity"] * item["price"] for item in cart.values())
        return jsonify({"code": 200, "message": "Product removed from cart", "cart": cart, "total_price": total_price}), 200
    else:
        return jsonify({"code": 404, "error": "Product not found in cart"}), 404


@app.route('/cart', methods=['GET'])
def view_cart():
    """
    Get all items in the cart and total price.
    """
    total_price = sum(item["quantity"] * item["price"] for item in cart.values())
    return jsonify({"code": 200, "cart": cart, "total_price": total_price}), 200

@app.route('/cart/clear', methods=['POST'])
def clear_cart():
    """
    Clear all items from cart after successful payment
    """
    cart.clear()
    return jsonify({"code":200, "messgae": "Cart has been successfully cleared."})


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)  # Enable logging at debug level
    app.run(host='0.0.0.0', port=5201, debug=True)
