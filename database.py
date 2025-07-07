import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

response = (
    supabase.table("user_data")
    .select("pdf_vector")
    .eq("id", 1)
    .execute()
)

