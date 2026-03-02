# supabase_client.py
import os
from supabase import create_client

class Config:
    # Lee las variables de entorno o deja vacío
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

def conectar_db():
    """
    Retorna un cliente de Supabase listo para usar.
    Verifica que las variables de entorno estén presentes.
    """
    if not Config.SUPABASE_URL or not Config.SUPABASE_KEY:
        print("❌ Configuración Supabase incompleta")
        print("DEBUG SUPABASE_URL:", Config.SUPABASE_URL)
        print("DEBUG SUPABASE_KEY presente:", bool(Config.SUPABASE_KEY))
        return None
    try:
        client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        return client
    except Exception as e:
        print("❌ Error conectando a Supabase:", e)
        return None

def obtener_minutos(phone):
    """
    Devuelve los minutos disponibles de un usuario.
    Retorna 0 si no existe el usuario o hay error.
    """
    db = conectar_db()
    if not db:
        return 0
    try:
        res = db.table("users").select("balance_minutes").eq("phone", phone).maybe_single().execute()
        print("DEBUG obtener_minutos res:", res.data)
        if res.data and 'balance_minutes' in res.data:
            return res.data['balance_minutes']
        else:
            print(f"⚠️ Usuario {phone} no encontrado o sin balance")
            return 0
    except Exception as e:
        print("❌ Error en obtener_minutos:", e)
        return 0

def restar_minuto(phone):
    """
    Resta un minuto usando la función RPC 'decrement_minutes' en Supabase.
    Retorna True si se logró, False si hubo error.
    """
    db = conectar_db()
    if not db:
        return False
    try:
        res = db.rpc("decrement_minutes", {"user_phone": phone}).execute()
        print("DEBUG restar_minuto res:", res.data)
        return True
    except Exception as e:
        print("❌ Error en restar_minuto:", e)
        return False

def restar_minuto_y_obtener_balance(phone):
    """
    Resta un minuto y devuelve el nuevo balance.
    Esto evita inconsistencias al leer el balance después.
    """
    db = conectar_db()
    if not db:
        return 0
    try:
        res = db.rpc("decrement_minutes", {"user_phone": phone}).execute()
        print("DEBUG restar_minuto_y_obtener_balance res:", res.data)
        # Si tu RPC retorna el balance actualizado, úsalo
        if res.data and 'balance_minutes' in res.data:
            return res.data['balance_minutes']
        # Si no, vuelve a leer de la tabla
        return obtener_minutos(phone)
    except Exception as e:
        print("❌ Error en restar_minuto_y_obtener_balance:", e)
        return 0
