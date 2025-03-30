from supabase import create_client, Client
import os
from dotenv import load_dotenv

# load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")


print(f"SUPABASE_URL: {SUPABASE_URL}")
print(f"SUPABASE_KEY: {SUPABASE_KEY}")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_supabase():
    return supabase