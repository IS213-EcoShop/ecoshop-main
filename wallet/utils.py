import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_or_create_wallet(user_id):
    result = supabase.table("wallets").select("*").eq("user_id", user_id).execute()
    if result.data:
        return result.data[0]
    # Create new wallet if not found
    new_wallet = {"user_id": user_id, "points": 0, "vouchers": []}
    supabase.table("wallets").insert(new_wallet).execute()
    return new_wallet

def credit_wallet(user_id, amount):
    wallet = get_or_create_wallet(user_id)
    new_points = wallet['points'] + amount
    supabase.table("wallets").update({"points": new_points}).eq("user_id", user_id).execute()
    return new_points

def debit_wallet(user_id, amount):
    wallet = get_or_create_wallet(user_id)
    if wallet['points'] < amount:
        return None
    new_points = wallet['points'] - amount
    supabase.table("wallets").update({"points": new_points}).eq("user_id", user_id).execute()
    return new_points

def get_wallet_balance(user_id):
    wallet = get_or_create_wallet(user_id)
    return wallet['points']