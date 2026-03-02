from supabase import create_client
from config import Config

def get_client():
    """Conexión segura que no tumba el servidor si falta la key al inicio"""
    if not Config.SUPABASE_URL or not Config.SUPABASE_KEY:
        return None
    try:
        return create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
    except:
        return None

def obtener_minutos(phone):
    client = get_client()
    if not client: return 0
    try:
        res = client.table("users").select("balance_minutes").eq("phone", phone).single().execute()
        return res.data['balance_minutes'] if res.data else 0
    except:
        return 0

def restar_minuto(phone):
    client = get_client()
    if client:
        try:
            client.rpc("decrement_minutes", {"user_phone": phone}).execute()
        except Exception as e:
            print(f"Error cobro: {e}")
