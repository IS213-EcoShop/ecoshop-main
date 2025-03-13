from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import stripe
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure MYSQL Database
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("MYSQL_DATABASE_URI")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Stripe API Key
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# Define Payment Model
class Payment(db.Model): 
    __tablename__ = 'payments'
    paymentID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    userID = db.Column(db.Integer, nullable=False)
    transactionDesc = db.Column(db.String(2048), nullable=False)
    amount = db.Column(db.Numeric(10,2), nullable=False)
    currency = db.Column(db.String(10), nullable=False)
    payment_status = db.Column(db.Enum('pending', 'successful', 'failed'), nullable=False, default='pending')
    stripe_payment_id = db.Column(db.String(255), unique=True, nullable=True)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())

# Create Tables
with app.app_context():
    db.create_all

#Create a Payment Session
@app.route('/payment', methods=['POST'])
def create_payment():
    data = request.json
    user_id = data.get('userID')
    amount = data.get('amount')
    currency = data.get('currency', 'usd')
    description = data.get('transactionDesc', 'Eco-Friendly Purchase')

    try:
        # Create a Stripe Checkout session
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': currency,
                    'product_data': {'name': description},
                    'unit_amount': int(amount * 100)
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=os.getenv("SUCCESS_URL"),
            cancel_url=os.getenv("CANCEL_URL"),
        )

        # Store payment in DB
        new_payment = Payment(
            userID=user_id,
            transactionDesc=description,
            amount=amount,
            currency=currency,
            payment_status='pending',
            stripe_payment_id=session.id
        )
        db.session.add(new_payment)
        db.session.commit()

        return jsonify({'paymentID': new_payment.paymentID, 'stripe_session_url': session.url}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
# Retrieve a Payment by ID
@app.route('/payment/<int:paymentID>', methods=['GET'])
def get_payment(paymentID):
    payment = Payment.query.get(paymentID)
    if not payment:
        return jsonify({'error': 'Payment not found'}), 404
    return jsonify({
        'paymentID': payment.paymentID,
        'userID': payment.userID,
        'transactionDesc': payment.transactionDesc,
        'amount': float(payment.amount),
        'currency': payment.currency,
        'payment_status': payment.payment_status,
        'stripe_payment_id': payment.stripe_payment_id,
        'created_at': payment.created_at
    }), 200

# Retrieve all Payments by User
@app.route('/payments/user/<int:userID>', methods=['GET'])
def get_user_payments(userID):
    payments = Payment.query.filter_by(userID=userID).all()
    return jsonify([{
        'paymentID': p.paymentID,
        'transactionDesc': p.transactionDesc,
        'amount': float(p.amount),
        'currency': p.currency,
        'payment_status': p.payment_status,
        'stripe_payment_id': p.stripe_payment_id,
        'created_at': p.created_at
    } for p in payments]), 200

# Handle Stripe Webhook
@app.route('/payment/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            payment = Payment.query.filter_by(stripe_payment_id=session['id']).first()
            if payment:
                payment.payment_status = 'successful'
                db.session.commit()
        return '', 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
