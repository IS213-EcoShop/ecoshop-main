from flask import Flask, json, request, jsonify
import stripe
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime, timezone
import pika
import json

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Initialize Supabase
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# Stripe API Key
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# Create a Payment Session
@app.route('/payment', methods=['POST'])
def create_payment():
    data = request.json
    print(f"Received request data: {data}")  # Debugging log

    user_id = data.get('userID')
    amount = data.get('amount')
    currency = data.get('currency', 'SGD')
    cart_details = data.get('cart', [])

    try:
        # Create a Stripe Checkout session
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': currency,
                    'product_data': {'name': 'Eco-friendly Purchase'},
                    'unit_amount': int(amount * 100)  # Stripe requires amount in cents
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=os.getenv("SUCCESS_URL"),
            cancel_url=os.getenv("CANCEL_URL"),
        )

        print(f"Stripe session created: {session.id}")  # Debugging log

        # Store payment in Supabase, including address and postal code
        response = supabase.table("payments").insert({
            "userID": user_id,
            "amount": amount,
            "currency": currency,
            "payment_status": "pending",
            "cart_details": json.dumps(cart_details),
            "stripe_payment_id": session.id,
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        print(f"Supabase insert response: {response}")  # Debugging log

        return jsonify({'paymentID': session.id, 'stripe_session_url': session.url}), 201
    except Exception as e:
        print(f"Error in create_payment(): {str(e)}")  # Log the full error
        return jsonify({'error': str(e)}), 500

# Retrieve a Payment by ID
@app.route('/payment/<string:paymentID>', methods=['GET'])
def get_payment(paymentID):
    response = supabase.table("payments").select("*").eq("stripe_payment_id", paymentID).execute()
    if not response.data:
        return jsonify({'error': 'Payment not found'}), 404
    return jsonify(response.data[0]), 200

# Retrieve all Payments by User
@app.route('/payments/user/<int:userID>', methods=['GET'])
def get_user_payments(userID):
    response = supabase.table("payments").select("*").eq("userID", userID).execute()
    return jsonify(response.data), 200
    
# Handle Stripe Webhook
@app.route('/payment/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    event = None

    try:
        # If there's an endpoint secret, verify the signature
        if endpoint_secret:
            event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        else:
            # If no endpoint secret, just parse the payload as JSON
            event = json.loads(payload)
    except json.decoder.JSONDecodeError as e:
        print('⚠️ Webhook error while parsing the request: ' + str(e))
        return jsonify(success=False), 400
    except stripe.error.SignatureVerificationError as e:
        print('⚠️ Webhook signature verification failed: ' + str(e))
        return jsonify(success=False), 400

    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        print(f"Checkout session completed for session ID: {session['id']}")

        # Look up the session ID in Supabase and update the payment status
        response = supabase.table("payments").select("*").eq("stripe_payment_id", session['id']).execute()
        if response.data:
            # Update payment status in Supabase
            update_response = supabase.table("payments").update({"payment_status": "successful"}).eq("stripe_payment_id", session['id']).execute()
            print(f"Updated payment status in Supabase: {update_response}")

            # Send a message to RabbitMQ (place_order service will consume it)
            connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
            channel = connection.channel()

            # Ensure the payment queue exists
            channel.queue_declare(queue='payment_queue')

            # Send the message to RabbitMQ
            message = {
                'paymentID': session['id'],
                'status': 'successful',
                'userID': response.data[0]['userID']
            }
            channel.basic_publish(
                exchange='',
                routing_key='payment_queue',
                body=json.dumps(message)
            )
            print("Publishing message to RabbitMQ with routing key=payment_queue")
            
            connection.close()

        else:
            print(f"No matching payment found in Supabase for session ID: {session['id']}")

    else:
        print(f"Unhandled event type: {event['type']}")

    return jsonify(success=True), 200

    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5202, debug=True)
