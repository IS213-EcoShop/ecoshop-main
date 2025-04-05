import os
import json
import pika
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def list_pending_trades():
    res = supabase.table("trade_ins").select("*").eq("status", "pending").execute()
    return res.data

def publish_event(event):
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
        channel = connection.channel()

        channel.exchange_declare(exchange="events.topic", exchange_type="topic", durable= True)

        routing_key = event.get("type", "trade.unknown").lower()

        channel.basic_publish(
            exchange="events.topic",
            routing_key=routing_key,
            body=json.dumps(event),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        connection.close()
        print(f"Published event to topic exchange: {routing_key} -> {event}")
    except Exception as e:
        print(f"Failed to publish event: {e}")

def update_trade_status(trade_id, status):
    # Update trade status in Supabase
    result = supabase.from_("trade_ins").update({"status": status}).eq("id", trade_id).execute()
    if result.data:
        trade = result.data[0]
        
        # If accepted, publish TRADE_IN_SUCCESS event
        if status == "accepted":
            publish_event({
                "type": "TRADE_IN_SUCCESS",
                "user_id": trade["user_id"],
                "trade_id": trade_id
            })
        return trade
    return None


# import os
# from supabase import create_client
# import requests

# SUPABASE_URL = os.getenv("SUPABASE_URL")
# SUPABASE_KEY = os.getenv("SUPABASE_KEY")
# #EMAIL_SERVICE_URL = os.getenv("EMAIL_SERVICE_URL")

# supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# def list_pending_trades():
#     res = supabase.table("trade_ins").select("*").eq("status", "pending").execute()
#     return res.data

# def update_trade_status(trade_id, status):
#     res = supabase.from_("trade_ins").update({"status": status}).eq("id", trade_id).execute()
#     return res.data[0] if res.data else None

# # def notify_user(user_id, status):
# #     try:
# #         payload = {
# #             "user_id": user_id,
# #             "subject": "Your Trade-In Status",
# #             "body": f"Your trade-in request has been {status.upper()}."
# #         }
# #         r = requests.post(EMAIL_SERVICE_URL, json=payload, timeout=5)
# #         return r.status_code == 200
# #     except Exception as e:
# #         print(f"Email notification failed: {e}")
# #         return False


from flask_cors import CORS

def enable_cors(app):
    """Enable CORS for the Flask app."""
    CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}})