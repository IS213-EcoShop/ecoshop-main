import os
from supabase import create_client
import requests

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
#EMAIL_SERVICE_URL = os.getenv("EMAIL_SERVICE_URL")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def list_pending_trades():
    res = supabase.table("trade_ins").select("*").eq("status", "pending").execute()
    return res.data

def update_trade_status(trade_id, status):
    res = supabase.from_("trade_ins").update({"status": status}).eq("id", trade_id).execute()
    return res.data[0] if res.data else None

# def notify_user(user_id, status):
#     try:
#         payload = {
#             "user_id": user_id,
#             "subject": "Your Trade-In Status",
#             "body": f"Your trade-in request has been {status.upper()}."
#         }
#         r = requests.post(EMAIL_SERVICE_URL, json=payload, timeout=5)
#         return r.status_code == 200
#     except Exception as e:
#         print(f"Email notification failed: {e}")
#         return False