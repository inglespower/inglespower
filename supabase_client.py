from supabase import create_client
from config import Config

supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

def obtener_minutos(phone):
    res = supabase.table("users").select("minutes").eq("phone", phone).single().execute()
    return res.data["minutes"] if res.data else 0

def restar_minuto(phone):
    # Asume que tienes una columna 'minutes' en tu tabla 'users'
    minutos_actuales = obtener_minutos(phone)
    if minutos_actuales > 0:
        supabase.table("users").update({"minutes": minutos_actuales - 1}).eq("phone", phone).execute()
