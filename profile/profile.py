import logging as log
from flask import Flask, request, jsonify
import utils.amqp_lib as rabbit
from utils.supabase import get_supabase

app = Flask(__name__)

# Simple logging configuration
log.basicConfig(level=log.DEBUG)

supabase = get_supabase()

# RabbitMQ 
RABBITMQ_HOST = "rabbitmq"
RABBITMQ_PORT = 5672
NOTIF_EXCHANGE_NAME = 'notification_exchange'

@app.route('/signup', methods=['POST'])
def create_user():
    """
    Create a new user.
    """
    log.info("Received signup request")
    data = request.json
    email = data.get('email')
    password = data.get('password')
    name = data.get('name')

    log.debug(f"Received data: {data}")  

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    try:
        # Insert user into Supabase
        response = supabase.table('users').insert({
            'name': name,
            'password': password,
            'email': email
        }).execute()

        # Establish connection to RabbitMQ
        connection, channel = rabbit.connect(
            RABBITMQ_HOST, 
            RABBITMQ_PORT, 
            NOTIF_EXCHANGE_NAME, 
            "topic"
        )
        
        rabbit.publish_message(
            channel, 
            NOTIF_EXCHANGE_NAME, 
            "email.welcome", 
            {'email': email, 'name': name}
        )

        connection.close()
        
        log.info(f"User {email} created successfully.")
        return jsonify({"status_code": 200, "status": "success", "message": "User created successfully"}), 200
    

    except Exception as e:
        log.error(f"Error creating user: {str(e)}")
        return jsonify({"status_code": 400, "status": "error", "message": str(e)}), 400



@app.route('/create_profile/<user_id>', methods=['PUT'])
def create_profile(user_id):
    data = request.json

    try:
        user_id = int(user_id)
    except ValueError:
        return jsonify({"error": "Invalid user_id format"}), 400

    profile_data = {
        "user_id": int(user_id),
        "phone": data.get("phone"),
        "address": data.get("address")
    }

    response = supabase.table("users").update(profile_data).eq("user_id", user_id).execute()

    if response:
        return jsonify({"message": "Profile created successfully."}), 201
    else:
        return jsonify({"error": "Error creating profile."}), 400

@app.route('/profile/<user_id>', methods=['GET'])
def get_profile(user_id):
    try:
        response = (
            supabase.table("users")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )

        if response.data:
            return jsonify({"profile": response.data[0]}), 200
        else:
            return jsonify({"error": "User profile not found"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

# @app.route('/signin', methods=['GET'])
# def sign_in():
#     """
#     Sign in user
#     """
#     data = request.json
#     email = data.get('email')
#     password = data.get('password')

#     log.debug(f"Received sign-in request: {data}")

#     if not email or not password:
#         return jsonify({"status": "error", "message": "Email and password are required"}), 400
 
#     try:
#         response = supabase.auth.sign_in_with_password({
#             'email': email,
#             'password': password
#         })
#         return jsonify(
#         {"status": "success", 
#         "message": "User Signed in Successfully",
#         "userid": response.user.id}
#         ), 200
    
#     except Exception as e:
#         print("Error:", e)
#         return jsonify({"status_code": 400, "status": "error", "message": str(e)}) ,400


# @app.route("/offboard", methods=["DELETE"]) #WIP
# def delete_user():
#     try:
#         # user = supabase.auth.get_user()

#         user = {"id" : "1d3c8b95-a217-481c-8931-d89a78adaecb"}
#         if not user:
#             return jsonify({"error": "No user is logged in"}), 400

#         response = supabase.auth.admin.delete_user(user.id)
        
#         if response.error:
#             print(f"Error deleting user: {response.error}")
#             return jsonify({"error": "could not delete"}), 400
#         else:
#             print(f"User with ID {user} deleted successfully.")
#             return jsonify({"status": "success","message":"user deleted"}), 400
#     except Exception as e:
#         print(f"An error occurred: {str(e)}")
#         return jsonify({"status_code": 400, "status": "error", "message": str(e)}) ,400

if __name__ == '__main__':
    NOTIF_QUEUES = {"notification_queue" : "email.*"}

    rabbit.connect(
        RABBITMQ_HOST, 
        RABBITMQ_PORT, 
        NOTIF_EXCHANGE_NAME, 
        "topic", 
        NOTIF_QUEUES
    )

    app.run(host='0.0.0.0', port=5001, debug=True)
