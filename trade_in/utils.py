import os
from supabase import create_client
from werkzeug.utils import secure_filename
import uuid
from flask_cors import CORS

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def upload_image_to_supabase(image_file):
    original_filename = secure_filename(image_file.filename)
    unique_prefix = str(uuid.uuid4())
    filename = f"{unique_prefix}_{original_filename}"
    file_content = image_file.read()
    supabase.storage.from_(SUPABASE_BUCKET).upload(filename, file_content, {"content-type": image_file.mimetype})
    public_url = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(filename)
    return filename, public_url

def create_trade_in(user_id, product_name, image_url, condition):
    data = {
        "user_id": user_id,
        "product_name": product_name,
        "image_url": image_url,
        "condition": condition,
        "status": "pending"
    }
    response = supabase.table("trade_ins").insert(data).execute()
    return response.data[0]

def get_trade_status(trade_id):
    result = supabase.table("trade_ins").select("*").eq("id", trade_id).execute()
    if result.data:
        return result.data[0]
    return None

def get_trade_history(user_id):
    result = supabase.table("trade_ins").select("product_name, created_at, image_url, condition, status").eq("user_id", user_id).order("created_at", desc=True).execute()
    return result.data

def enable_cors(app):
    CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}})