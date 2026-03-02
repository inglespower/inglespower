# supabase_client.py
from supabase import create_client
from config import Config

def conectar_db():
    """Conexión a Supabase bajo demanda."""
    if not Config.SUPABASE_URL or not Config.SUPABASE_KEY:
        return None
    try:
        return create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
    except Exception as e:
        print("Error conectando a Supabase:", e)
        return None

def obtener_minutos(phone: str) -> int:
    """Devuelve los minutos disponibles del usuario."""
    db = conectar_db()
    if not db:
        return 0
    try:
        res = db.table("users").select("balance_minutes").eq("phone", phone).maybe_single().execute()
        if res is None or not res.data:
            return 0
        return res.data.get("balance_minutes", 0)
    except Exception as e:
        print("❌ Error en obtener_minutos:", e)
        return 0

def restar_minuto_y_obtener_balance(phone: str) -> int:
    """Resta un minuto y devuelve el balance actualizado."""
    db = conectar_db()
    if not db:
        return 0
    try:
        # Usar RPC si tienes, o actualizar manualmente
        try:
            res = db.rpc("decrement_minutes", {"user_phone": phone}).execute()
            if res is None or not res.data:
                raise Exception("RPC no devolvió datos")
            return res.data.get("balance_minutes", 0)
        except Exception:
            # Fallback: actualizar manualmente
            current = obtener_minutos(phone)
            nuevo = max(current - 1, 0)
            db.table("users").update({"balance_minutes": nuevo}).eq("phone", phone).execute()
            return nuevo
    except Exception as e:
        print("❌ Error en restar_minuto_y_obtener_balance:", e)
        return 0
