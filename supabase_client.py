from supabase import create_client
from config import Config

supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

def obtener_minutos(phone):
    res = supabase.table("users").select("balance_minutes").eq("phone", phone).single().execute()
    return res.data['balance_minutes'] if res.data else 0

def restar_minuto(phone):
    supabase.rpc("decrement_minutes", {"user_phone": phone}).execute()
