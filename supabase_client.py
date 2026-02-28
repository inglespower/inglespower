import os
from supabase import create_client

# --- CONEXIÓN CORREGIDA PARA RENDER ---
# En lugar de importar de config.py, leemos directamente del sistema
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Verificación de seguridad para evitar el error "supabase_key is required"
if not SUPABASE_URL or not SUPABASE_KEY:
    print(f"ERROR CRÍTICO: SUPABASE_URL es {SUPABASE_URL}")
    print(f"ERROR CRÍTICO: SUPABASE_KEY es {SUPABASE_KEY}")
    raise ValueError("No se encontraron las credenciales de Supabase. Revisa las Environment Variables en Render.")

# Inicialización del cliente
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- TUS FUNCIONES ORIGINALES (SIN CAMBIOS EN LA LÓGICA) ---

def get_minutes(phone):
    res = supabase.table("minutes").select("*").eq("phone_number", phone).execute()
    if res.data:
        return res.data[0]["minutes_remaining"]
    return 0

def add_minutes(phone, minutes):
    res = supabase.table("minutes").select("*").eq("phone_number", phone).execute()
    if res.data:
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
        supabase.table("minutes").update({"minutes_remaining": m - 1}).eq("phone_number", phone).execute()
        return True
    return False
