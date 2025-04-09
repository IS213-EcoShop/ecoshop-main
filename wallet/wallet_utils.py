import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_or_create_wallet(user_id):
    result = supabase.table("wallet").select("*").eq("user_id", user_id).execute()
    if result.data:
        return result.data[0]
    # Create new wallet with 0 points and total_points
    new_wallet = {
        "user_id": user_id,
        "points": 0,
        "total_points": 0,
        "vouchers": []
    }
    supabase.table("wallet").insert(new_wallet).execute()
    return new_wallet

def credit_wallet(user_id, amount):
    wallet = get_or_create_wallet(user_id)
    # new_points = wallet.get['points', 0] + amount
    new_points = wallet.get('points', 0) + amount
    new_total = wallet.get('total_points', 0) + amount

    supabase.table("wallet").update({
        "points": new_points,
        "total_points": new_total
    }).eq("user_id", user_id).execute()

    print(f"[✓] Wallet credited for user {user_id} with {amount} points.")
    return {
        "points": new_points,
        "total_points": new_total
    }

def debit_wallet(user_id, amount):
    wallet = get_or_create_wallet(user_id)
    current_points = wallet.get('points', 0)
    if current_points < amount:
        print(f"[!] Insufficient points for user {user_id}")
        return None
    # if wallet['points'] < amount:
    #     return None
    new_points = wallet['points'] - amount
    supabase.table("wallet").update({"points": new_points}).eq("user_id", user_id).execute()
    return {
        "points": new_points,
        "total_points": wallet.get('total_points', 0)  # doesn't change on debit
    }

def get_wallet_balance(user_id):
    wallet = get_or_create_wallet(user_id)
    return {
        # "points": wallet['points'],
        "points": wallet.get('points', 0),
        "total_points": wallet.get('total_points', 0)
    }

def get_voucher_balance(user_id):
    voucher = get_or_create_wallet(user_id)
    return {
        "vouchers": voucher.get('vouchers', 0)
    }

def delete_voucher_from_wallet(user_id, voucher_id):
    """Delete a single instance of a voucher from a user's wallet."""
    try:
        # Get the current wallet
        result = supabase.table("wallet").select("*").eq("user_id", user_id).execute()
        
        if not result.data:
            print(f"No wallet found for user {user_id}")
            return None
            
        wallet = result.data[0]
        vouchers = wallet.get('vouchers', [])
        
        # Find the index of the first occurrence of the voucher
        voucher_index = None
        for i, voucher in enumerate(vouchers):
            if voucher.get('id') == voucher_id:
                voucher_index = i
                break
        
        # If voucher not found, return None
        if voucher_index is None:
            print(f"Voucher {voucher_id} not found in wallet for user {user_id}")
            return None
        
        # Remove only the first occurrence of the voucher
        removed_voucher = vouchers.pop(voucher_index)
        
        # Update the wallet
        update_result = supabase.table("wallet").update({
            "vouchers": vouchers
        }).eq("user_id", user_id).execute()
        
        print(f"Deleted one instance of voucher {voucher_id} from wallet for user {user_id}")
        print(f"Removed voucher details: {removed_voucher}")
        return True
        
    except Exception as e:
        print(f"Error deleting voucher: {e}")
        return None


# import os
# from supabase import create_client
# from dotenv import load_dotenv

# load_dotenv()
# SUPABASE_URL = os.getenv("SUPABASE_URL")
# SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# def get_or_create_wallet(user_id):
#     result = supabase.table("wallets").select("*").eq("user_id", user_id).execute()
#     if result.data:
#         return result.data[0]
#     # Create new wallet if not found
#     new_wallet = {"user_id": user_id, "points": 0, "vouchers": []}
#     supabase.table("wallets").insert(new_wallet).execute()
#     return new_wallet

# def credit_wallet(user_id, amount):
#     wallet = get_or_create_wallet(user_id)
#     new_points = wallet['points'] + amount
#     supabase.table("wallets").update({"points": new_points}).eq("user_id", user_id).execute()
#     new_total = wallet.get('total_points', 0) + amount
#     supabase.table("wallets").update({"points": new_points,"total_points": new_total}).eq("user_id", user_id).execute()

#     # do i also return totalpoints?
#     return new_points

# def debit_wallet(user_id, amount):
#     wallet = get_or_create_wallet(user_id)
#     if wallet['points'] < amount:
#         return None
#     new_points = wallet['points'] - amount
#     supabase.table("wallets").update({"points": new_points}).eq("user_id", user_id).execute()
#     return new_points

# def get_wallet_balance(user_id):
#     wallet = get_or_create_wallet(user_id)
#     return wallet['points']


from flask_cors import CORS

def enable_cors(app):
    """Enable CORS for the Flask app."""
    CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}})