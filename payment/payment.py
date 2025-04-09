from flask import Flask, json, request, jsonify
import stripe
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime, timezone
import pika
import json
import utils.amqp_lib as rabbit
from utils.cors_config import enable_cors
from flask import render_template_string

# Load environment variables
load_dotenv()

app = Flask(__name__)
enable_cors(app)

# Initialize Supabase
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# Stripe API Key
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# Initialize AMQP variables
PAYMENT_EXCHANGE_NAME = "payment_exchange"
PAYMENT_QUEUE_NAME = "payment_queue"
PAYMENT_ROUTING_KEY = "payment_success"

# Create a Payment Session
@app.route('/payment', methods=['POST'])
def create_payment():
    data = request.json
    print(f"Received request data: {data}")  # Debugging logs

    user_id = data.get('userID')
    amount = data.get('amount')
    currency = data.get('currency', 'SGD')
    cart_details = data.get('cart', [])
    
    # Get voucher information if provided
    voucher_id = data.get('voucherId')
    voucher_value = data.get('voucherValue')
    original_amount = data.get('originalAmount')

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

        # Prepare payment data for Supabase
        payment_data = {
            "userID": user_id,
            "amount": amount,
            "currency": currency,
            "payment_status": "pending",
            "cart_details": json.dumps(cart_details),
            "stripe_payment_id": session.id,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Add voucher information if provided
        if voucher_id:
            payment_data["voucherId"] = voucher_id
            payment_data["voucherValue"] = voucher_value
            payment_data["originalAmount"] = original_amount
            print(f"Storing voucher info: voucherId={voucher_id}, value={voucher_value}")

        # Store payment in Supabase
        response = supabase.table("payments").insert(payment_data).execute()

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
@app.route('/payment/user/<int:userID>', methods=['GET'])
def get_user_payments(userID):
    response = supabase.table("payments").select("*").eq("userID", userID).execute()
    return jsonify(response.data), 200

# Handle Stripe Webhook
@app.route('/payment/webhook', methods=['POST'])
def stripe_webhook():
    print("========== PAYMENT WEBHOOK ==========")
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    event = None

    try:
        # Verify event with signature
        if endpoint_secret:
            event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        else:
            event = json.loads(payload)
    except json.decoder.JSONDecodeError as e:
        print('Webhook error while parsing the request: ' + str(e))
        return jsonify(success=False), 400
    except stripe.error.SignatureVerificationError as e:
        print('Webhook signature verification failed: ' + str(e))
        return jsonify(success=False), 400

    event_type = event['type']
    print(f"Received Stripe event: {event_type}")

    if event_type == 'checkout.session.completed':
        session = event['data']['object']
        print(f"Checkout session completed for session ID: {session['id']}")

        response = supabase.table("payments").select("*").eq("stripe_payment_id", session['id']).execute()
        if response.data:
            payment_data = response.data[0]
            update_response = supabase.table("payments").update(
                {"payment_status": "successful"}).eq("stripe_payment_id", session['id']).execute()
            print(f"Updated payment status in Supabase: {update_response}")

            connection, channel = rabbit.connect("rabbitmq", 5672, PAYMENT_EXCHANGE_NAME, "topic")

            # Create message with all necessary data including voucher information
            message = {
                'paymentID': session['id'],
                'status': 'successful',
                'userID': payment_data['userID']
            }
            
            # Add voucher information if it exists in the payment data
            # These fields would have been stored when creating the payment
            if 'voucherId' in payment_data:
                message['voucherId'] = payment_data['voucherId']
                message['voucherValue'] = payment_data['voucherValue']
                message['originalAmount'] = payment_data['originalAmount']
                print(f"Including voucher info in message: voucherId={payment_data['voucherId']}")

            print(f"Publishing message to topic exchange '{PAYMENT_EXCHANGE_NAME}' with routing key='{PAYMENT_ROUTING_KEY}'")
            print(f"Message content: {json.dumps(message, indent=2)}")
            rabbit.publish_message(channel, PAYMENT_EXCHANGE_NAME, PAYMENT_ROUTING_KEY, message)
            connection.close()
        else:
            print(f"No matching payment found in Supabase for session ID: {session['id']}")

    elif event_type == 'checkout.session.expired':
        session = event['data']['object']
        print(f"Checkout session expired: {session['id']}")
        supabase.table("payments").update(
            {"payment_status": "expired"}).eq("stripe_payment_id", session['id']).execute()

    elif event_type == 'payment_intent.payment_failed':
        intent = event['data']['object']
        session_id = intent.get('metadata', {}).get('checkout_session_id')
        print(f"Payment failed for session: {session_id}")
        if session_id:
            supabase.table("payments").update(
                {"payment_status": "failed"}).eq("stripe_payment_id", session_id).execute()
        else:
            print("No checkout session ID in payment_intent metadata. Cannot update Supabase.")

    else:
        print(f"Unhandled event type: {event_type}")

    return jsonify(success=True), 200

# Payment success redirection
@app.route('/payment/success', methods=['GET'])
def order_success():
    return render_template_string('''
        <html>
        <head>
            <title>Payment Success</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    text-align: center;
                    background-color: #f4f4f4;
                    padding: 50px;
                }
                .container {
                    background: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
                    display: inline-block;
                }
                h1 {
                    color: #2d6a4f;
                }
                p {
                    font-size: 18px;
                    color: #333;
                }
                button {
                    background-color: #2d6a4f;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    font-size: 16px;
                    border-radius: 5px;
                    cursor: pointer;
                    margin-top: 20px;
                }
                button:hover {
                    background-color: #1b4332;
                }
            </style>
            <script>
                function closeTab() {
                    window.close();
                }
            </script>
        </head>
        <body>
            <div class="container">
                <h1>Payment Received</h1>
                <p>Thank you for buying with <strong>SustainaMart</strong>. You may now close this tab.</p>
                <button onclick="closeTab()">Close Tab</button>
            </div>
        </body>
        </html>
    ''')

# Payment canceled redirection
@app.route('/payment/cancel', methods=['GET'])
def order_cancel():
    return render_template_string('''
        <html>
        <head>
            <title>Payment Canceled</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    text-align: center;
                    background-color: #f4f4f4;
                    padding: 50px;
                }
                .container {
                    background: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
                    display: inline-block;
                }
                h1 {
                    color: #d00000;
                }
                p {
                    font-size: 18px;
                    color: #333;
                }
                button {
                    background-color: #d00000;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    font-size: 16px;
                    border-radius: 5px;
                    cursor: pointer;
                    margin-top: 20px;
                }
                button:hover {
                    background-color: #9d0208;
                }
            </style>
            <script>
                function closeTab() {
                    window.close();
                }
            </script>
        </head>
        <body>
            <div class="container">
                <h1>Payment Canceled</h1>
                <p>Your payment was not completed. You may try again later or return to the store.</p>
                <button onclick="closeTab()">Close Tab</button>
            </div>
        </body>
        </html>
    ''')


    
if __name__ == '__main__':
    rabbit.connect( #create the payment exchange name and queue
        "rabbitmq",
        5672,
        PAYMENT_EXCHANGE_NAME,
        "topic",
        {PAYMENT_QUEUE_NAME:PAYMENT_ROUTING_KEY}
    )
    app.run(host='0.0.0.0', port=5202, debug=True)