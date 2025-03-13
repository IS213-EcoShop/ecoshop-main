from flask import Flask, request, jsonify
from invokes import invoke_http
import logging
from flasgger import Swagger  # Import Swagger

app = Flask(__name__)
swagger = Swagger(app)  # Initialize Swagger with Flask app

# External product API URL (updated with productId placeholder)
PRODUCT_API_URL = "https://personal-o2kymv2n.outsystemscloud.com/SustainaMart/rest/v1/products/{}/"

# In-memory cart storage
cart = {}

def get_product_by_id(product_id):
    """
    Helper function to fetch product details by product ID.
    ---
    parameters:
      - name: productId
        in: path
        type: integer
        required: true
        description: The ID of the product
    responses:
      200:
        description: The product data
        schema:
          type: object
          properties:
            Product:
              type: object
              properties:
                Name:
                  type: string
                  example: "Eco-Friendly T-Shirt"
                Price:
                  type: number
                  format: float
                  example: 29.99
                Stock:
                  type: integer
                  example: 100
                Image:
                  type: string
                  example: "http://example.com/images/t-shirt.jpg"
      400:
        description: Product not found
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
    ---
    parameters:
      - name: productId
        in: body
        type: integer
        required: true
        description: The ID of the product to be added to the cart
        example: 101
      - name: quantity
        in: body
        type: integer
        required: true
        description: The quantity of the product
        example: 2
    responses:
      200:
        description: Cart updated successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Cart updated successfully"
            cart:
              type: object
              additionalProperties:
                type: object
                properties:
                  productId:
                    type: integer
                    example: 101
                  name:
                    type: string
                    example: "Eco-Friendly T-Shirt"
                  price:
                    type: number
                    format: float
                    example: 29.99
                  quantity:
                    type: integer
                    example: 2  # Updated quantity
                  image_url:
                    type: string
                    example: "http://example.com/images/t-shirt.jpg"
              example:
                # Correct cart response showing a single product
                {
                  "101": {
                    "productId": 101,
                    "name": "Eco-Friendly T-Shirt",
                    "price": 29.99,
                    "quantity": 2,
                    "image_url": "http://example.com/images/t-shirt.jpg"
                  }
                }
      400:
        description: Invalid product ID or quantity
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Invalid productId. Must be a positive integer."
    """
    data = request.json
    product_id = data.get("productId")
    quantity = data.get("quantity")

    # Validate that productId and quantity are valid
    if not isinstance(product_id, int) or product_id <= 0:
        return jsonify({"error": "Invalid productId. Must be a positive integer."}), 400
    
    if not isinstance(quantity, int) or quantity <= 0:
        return jsonify({"error": "Quantity must be a valid positive integer."}), 400

    # Log the received productId and quantity
    logging.debug(f"Received productId: {product_id}, quantity: {quantity}")

    # Fetch product details using helper function
    product = get_product_by_id(product_id)

    if not product:
        return jsonify({"error": "Invalid product ID"}), 400

    product_price = product["Price"]
    product_stock = product["Stock"]

    # Check if the requested quantity is available in stock
    if quantity > product_stock:
        return jsonify({"error": f"Not enough stock. Available: {product_stock}."}), 400

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

    return jsonify({"message": "Cart updated successfully", "cart": cart}), 200


@app.route('/cart/remove', methods=['DELETE'])
def remove_from_cart():
    """
    Remove product from cart.
    ---
    parameters:
      - name: productId
        in: body
        type: integer
        required: true
        description: The ID of the product to be removed from the cart
        example: 101
    responses:
      200:
        description: Product removed successfully from cart
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Product removed from cart"
            cart:
              type: object
              additionalProperties:
                type: object
                properties:
                  productId:
                    type: integer
                    example: 101
                  name:
                    type: string
                    example: "Eco-Friendly T-Shirt"
                  price:
                    type: number
                    format: float
                    example: 29.99
                  quantity:
                    type: integer
                    example: 2
                  image_url:
                    type: string
                    example: "http://example.com/images/t-shirt.jpg"
              example:
                # Updated cart after removing the product
                {}  # Empty cart after removal
      404:
        description: Product not found in cart
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Product not found in cart"
    """
    data = request.json
    product_id = data.get("productId")

    if not isinstance(product_id, int) or product_id <= 0:
        return jsonify({"error": "Invalid productId. Must be a positive integer."}), 400

    if product_id in cart:
        del cart[product_id]
        return jsonify({"message": "Product removed from cart", "cart": cart}), 200
    else:
        return jsonify({"error": "Product not found in cart"}), 404



@app.route('/cart', methods=['GET'])
def view_cart():
    """
    Get all items in the cart and total price.
    ---
    responses:
      200:
        description: Cart details with total price
        schema:
          type: object
          properties:
            cart:
              type: object
              additionalProperties:
                type: object
                properties:
                  productId:
                    type: integer
                    example: 101
                  name:
                    type: string
                    example: "Eco-Friendly T-Shirt"
                  price:
                    type: number
                    format: float
                    example: 29.99
                  quantity:
                    type: integer
                    example: 2
                  image_url:
                    type: string
                    example: "http://example.com/images/t-shirt.jpg"
            total_price:
              type: number
              format: float
              example: 59.98
    """
    total_price = sum(item["quantity"] * item["price"] for item in cart.values())
    return jsonify({"cart": cart, "total_price": total_price}), 200


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)  # Enable logging at debug level
    app.run(host='0.0.0.0', port=5000, debug=True)
