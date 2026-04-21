from supabase import create_client
from config import Config

supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

# -------------------------
# OBTENER MINUTOS
# -------------------------
def obtener_minutos(phone):
    try:
        res = supabase.table("users").select("minutes").eq("phone", phone).maybe_single().execute()
        return res.data["minutes"] if res.data else 0
    except:
        return 0


# -------------------------
# RESTAR MINUTO
# -------------------------
def restar_minuto(phone):
    minutos = obtener_minutos(phone)
    if minutos > 0:
        supabase.table("users").update({"minutes": minutos - 1}).eq("phone", phone).execute()
