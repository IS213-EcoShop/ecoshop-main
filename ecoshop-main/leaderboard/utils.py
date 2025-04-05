import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

def update_leaderboard(user_id, total_points):
    existing = supabase.table("leaderboard").select("*").eq("user_id", user_id).execute().data
    if existing:
        supabase.table("leaderboard").update({"total_points": total_points}).eq("user_id", user_id).execute()
    else:
        supabase.table("leaderboard").insert({"user_id": user_id, "total_points": total_points}).execute()

def get_top_leaderboard(limit=10):
    return supabase.table("leaderboard").select("*").order("total_points", desc=True).limit(limit).execute().data

from flask_cors import CORS

def enable_cors(app):
    """Enable CORS for the Flask app."""
    CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}})






# import os
# from supabase import create_client
# from dotenv import load_dotenv

# load_dotenv()
# SUPABASE_URL = os.getenv("SUPABASE_URL")
# SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# def get_top_users(limit=10):
#     res = supabase.table("wallet").select("user_id, total_points").order("total_points", desc=True).limit(limit).execute()
#     return res.data

# def get_user_rank(user_id):
#     wallets = supabase.table("wallet").select("user_id, total_points").order("total_points", desc=True).execute().data
#     for i, entry in enumerate(wallets):
#         if entry['user_id'] == user_id:
#             return {"rank": i + 1, "points": entry['points']}
#     return {"rank": None, "points": 0}