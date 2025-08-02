import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")

# Verifica se as variáveis de ambiente estão configuradas
if not url or not key:
    print("⚠️  Aviso: Variáveis SUPABASE_URL e SUPABASE_KEY não configuradas no arquivo .env")
    print("A API funcionará apenas para testes básicos.")

supabase: Client = create_client(url, key) if url and key else None

