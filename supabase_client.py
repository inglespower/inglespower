import os
from supabase import create_client

# 1. CONEXIÓN DIRECTA A LAS VARIABLES DE RENDER (Soluciona tu error actual)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Error: SUPABASE_URL o SUPABASE_KEY no configurados en el panel de Render.")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 2. TUS FUNCIONES (Corregidas para que lean bien los datos de la tabla)
def get_minutes(phone):
    res = supabase.table("minutes").select("*").eq("phone_number", phone).execute()
    # Supabase devuelve una lista, por eso usamos [0]
    if res.data and len(res.data) > 0:
        return res.data[0]["minutes_remaining"]
    return 0

def add_minutes(phone, minutes):
    res = supabase.table("minutes").select("*").eq("phone_number", phone).execute()
    if res.data and len(res.data) > 0:
        current = res.data[0]["minutes_remaining"]
        supabase.table("minutes").update({"minutes_remaining": current + minutes}).eq("phone_number", phone).execute()
    else:
        supabase.table("minutes").insert({
            "phone_number": phone,
            "minutes_remaining": minutes
        }).execute()

def subtract_minute(phone):
    m = get_minutes(phone)
    if m > 0:
        # Actualizamos restando 1
        supabase.table("minutes").update({"minutes_remaining": m - 1}).eq("phone_number", phone).execute()
        return True
    return False
