import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

def list_voucher_templates():
    return supabase.table("voucher_templates").select("*").execute().data

def get_user_wallet(user_id):
    result = supabase.table("wallet").select("*").eq("user_id", user_id).execute()
    return result.data[0] if result.data else None

def claim_voucher(user_id, voucher_id):
    wallet = get_user_wallet(user_id)
    if not wallet:
        return {"error": "Wallet not found"}, 404

    voucher = supabase.table("voucher_templates").select("*").eq("id", voucher_id).single().execute().data
    if not voucher:
        return {"error": "Voucher not found"}, 404

    if wallet["points"] < voucher["points_cost"]:
        return {"error": "Not enough points"}, 400

    new_points = wallet["points"] - voucher["points_cost"]

    # Add to user's vouchers
    claimed = wallet.get("vouchers", [])
    claimed.append({
        "id": voucher["id"],
        "name": voucher["name"],
        "value": voucher["value"],
        "expires_at": voucher.get("expires_at")
    })

    supabase.table("wallet").update({
        "points": new_points,
        "vouchers": claimed
    }).eq("user_id", user_id).execute()

    return {"status": "Voucher claimed", "vouchers": claimed}

from flask_cors import CORS

def enable_cors(app):
    """Enable CORS for the Flask app."""
    CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}})