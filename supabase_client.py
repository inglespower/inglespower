import os
from supabase import create_client
from config import Config

# Validamos que las llaves existan antes de conectar
if not Config.SUPABASE_URL or not Config.SUPABASE_KEY:
    print("ERROR: Faltan las credenciales de Supabase en Render Environment")
    supabase = None
else:
    supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

def obtener_minutos(phone):
    if not supabase: return 0
    try:
        res = supabase.table("users").select("balance_minutes").eq("phone", phone).single().execute()
        return res.data['balance_minutes'] if res.data else 0
    except:
        return 0

def restar_minuto(phone):
    if supabase:
        supabase.rpc("decrement_minutes", {"user_phone": phone}).execute()
