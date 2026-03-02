from supabase import create_client
from config import Config

def conectar_db():
    """Conexión bajo demanda para evitar errores de inicio en Render"""
    if not Config.SUPABASE_URL or not Config.SUPABASE_KEY:
        return None
    try:
        return create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
    except:
        return None

def obtener_minutos(phone):
    db = conectar_db()
    if not db: return 0
    try:
        res = db.table("users").select("balance_minutes").eq("phone", phone).single().execute()
        return res.data['balance_minutes'] if res.data else 0
    except:
        return 0

def restar_minuto(phone):
    db = conectar_db()
    if db:
        try:
            # Llama a la función RPC en tu Supabase
            db.rpc("decrement_minutes", {"user_phone": phone}).execute()
        except:
            pass
