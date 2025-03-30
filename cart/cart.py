import threading
import pika
import json
from flask import Flask, jsonify, request
from utils.supabase import get_supabase
import utils.amqp_lib as rabbit


supabase = get_supabase()

RABBITMQ_HOST = "rabbitmq"
RABBITMQ_PORT = 5672

CART_QUEUE_NAME = "cart_queue"
PLACE_ORDER_EXCHANGE_NAME = "place_order_exchange"

app = Flask(__name__)


@app.route('/cart/add', methods=['POST'])
def add_to_cart():
    """ Add a product to the cart or update quantity. """
    print("==================ADDING TO CART========================")
    data = request.json
    print(data)
    product = data.get("product")
    quantity = data.get("quantity")
    user_id = data.get("user_id")

    print("RECEIVED PRODUCT TO ADD")
    product_id = product["productId"]

    if not isinstance(product_id, int) or product_id <= 0:
        return jsonify({"code": 400, "error": "Invalid productId"}), 400
    

    if not isinstance(quantity, int) or quantity < 0:
        return jsonify({"code": 400, "error": "Quantity must be a positive integer"}), 400

    del product["Stock"]
    product["quantity"] = quantity
        
    try:
        response = (
            supabase.table("carts")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )
        print("RETRIEVED CART")
        print(response.data)

        if (response.data == [] ): #add product if no entry
            try:
                response = supabase.table('carts').insert({
                'user_id': user_id,
                'cart':{product_id : product}
                }).execute()
                return {"response":response.data}, 200
            except Exception as e:
                return {"error" : "Couldn't add to cart", "message":str(e)}, 404

        else:
            existing_cart = response.data[0]["cart"]  # user already has a cart
            
            if quantity == 0:
                del existing_cart[str(product_id)]
            else:
                existing_cart[str(product_id)] = product

            try:
                response = (
                    supabase.table("carts")
                    .update({"cart": existing_cart})
                    .eq("user_id", user_id)
                    .execute()
                )

                total_price = sum(item["quantity"] * item["Price"] for item in existing_cart.values())

                return jsonify({"code": 200, "message": "Cart updated successfully", "cart": existing_cart, "total_price": total_price, "response" : response.data}), 200
            except Exception as e:
                return {"error": "Couldn't update cart", "message": str(e)}, 404
        
    except Exception as e: 
        return {"error" : str(e)}, 500

@app.route('/cart/remove', methods=['PUT']) # replacement function to remove the entire product from the listing
def decrement_cart():
    """ Decrease the quantity of a product in the cart or remove it. """
    print("=============REMOVE PRODUCT FROM CART==================")
    data = request.json
    product_id = data.get("productId")
    user_id = data.get("user_id")

    if not isinstance(product_id, int) or product_id <= 0:
        return jsonify({"code": 400, "error": "Invalid productId"}), 400

    try:
        response = (supabase.table("carts")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )
        cart = response.data[0]["cart"]
        print(cart)

        if str(product_id) not in cart:
            print(str(product_id), cart)
            return jsonify({"code": 404, "error": "Product not found in cart"}), 404
        
        del cart[str(product_id)]

        try:
            response = (
                supabase.table("carts")
                .update({"cart": cart})
                .eq("user_id", user_id)
                .execute()
            )

            return jsonify({"code": 200, "message": "Product removed successfully", "cart": cart, "response" : response.data}), 200
        except Exception as e:
            return {"error": "Couldn't update removed cart", "message": str(e)}, 404

    except Exception as e:
        return {"error" : "Couldn't get user's cart", "message":str(e)}, 500



@app.route('/cart/<user_id>', methods=['GET'])
def view_cart(user_id):
    """ Get all items in the cart and total price. """
    print("====== GETTING USER'S CART INFO ======")
    print(user_id)
    try:
        response = (
            supabase.table("carts")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )

        total_price = sum(item["quantity"] * item["Price"] for item in response.data[0]["cart"].values())
        return jsonify({"code": 200, "cart": response.data[0]["cart"], "total_price": total_price}), 200
    except Exception as e:
        return {"error" : "User does not have a cart", "message" : str(e)}, 400

@app.route('/cart/clear/<user_id>', methods=['DELETE'])
def clear_cart(user_id):
    """ Clear all items from cart after successful payment """
    try:
        response = (
            supabase.table("carts")
            .delete()
            .eq("user_id", user_id)
            .execute()
        )
        return jsonify({"code": 200, "message": "Cart has been successfully cleared."})
    except Exception as e:
        return {"error" : "Could not delete user's cart", "message": str(e)}, 500

# This function will process messages from RabbitMQ
def callback(ch, method, properties, body):
    try:
        message = json.loads(body)
        print(f"Received message: {message}")
        
        user_id = message.get('user_id')

        print("Clearing the cart...")
        clear_cart(user_id)
        print("Cart has been cleared.")

    except Exception as e:
        print(f"Error processing message: {e}")
    finally:
        ch.basic_ack(delivery_tag=method.delivery_tag)


# Function to run the Flask app
def run_flask_app():
    app.run(host='0.0.0.0', port=5201)

if __name__ == '__main__':
    #REDUNDANCY 
    rabbit.connect(RABBITMQ_HOST, RABBITMQ_PORT, PLACE_ORDER_EXCHANGE_NAME, "fanout", {CART_QUEUE_NAME: ""})

    # Start the Flask app in a separate thread
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.start()

    # IS A CONSUMER
    rabbit.start_consuming(RABBITMQ_HOST, RABBITMQ_PORT, PLACE_ORDER_EXCHANGE_NAME, "fanout", CART_QUEUE_NAME, callback=callback)
