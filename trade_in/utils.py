import os
from supabase import create_client
import requests
from werkzeug.utils import secure_filename
import uuid

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET")
EMAIL_SERVICE_URL = os.getenv("EMAIL_SERVICE_URL")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# def upload_image_to_supabase(image_file):
#     filename = secure_filename(image_file.filename)
#     file_content = image_file.read()
#     supabase.storage.from_(SUPABASE_BUCKET).upload(filename, file_content, {"content-type": image_file.mimetype})
#     public_url = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(filename)
#     return filename, public_url

import uuid
from werkzeug.utils import secure_filename

def upload_image_to_supabase(image_file):
    original_filename = secure_filename(image_file.filename)
    # Generate a unique ID to avoid collisions
    unique_prefix = str(uuid.uuid4())
    filename = f"{unique_prefix}_{original_filename}"
    
    file_content = image_file.read()
    
    # Upload to Supabase
    supabase.storage.from_(SUPABASE_BUCKET).upload(
        filename,
        file_content,
        {"content-type": image_file.mimetype}
    )
    
    public_url = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(filename)
    return filename, public_url

def create_trade_in(user_id, product_name, image_url):
    data = {
        "user_id": user_id,
        "product_name": product_name,
        "image_url": image_url,
        "status": "pending"
    }
    response = supabase.table("trade_ins").insert(data).execute()
    return response.data[0]

def get_trade_status(trade_id):
    result = supabase.table("trade_ins").select("*").eq("id", trade_id).execute()
    if result.data:
        return result.data[0]
    return None

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
#         print("Notification failed:", e)
#         return False
