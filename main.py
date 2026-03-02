# main.py
from supabase_client import obtener_minutos, restar_minuto_y_obtener_balance, conectar_db

# Configuración inicial de minutos para usuarios nuevos
MINUTOS_INICIALES = 10

# Número de teléfono del usuario (en producción lo obtienes de la llamada)
phone = "+15555555555"

# Obtenemos los minutos del usuario
minutos = obtener_minutos(phone)

# Si no tiene minutos o no existe, creamos el usuario con saldo inicial
if minutos == 0:
    db = conectar_db()
    if db:
        try:
            # Verifica si el usuario ya existe
            existing = db.table("users").select("*").eq("phone", phone).maybe_single().execute()
            if not existing.data:
                db.table("users").insert({
                    "phone": phone,
                    "balance_minutes": MINUTOS_INICIALES
                }).execute()
                minutos = MINUTOS_INICIALES
                print(f"Usuario creado con {MINUTOS_INICIALES} minutos.")
            else:
                print("Usuario existe pero sin minutos. Por favor recarga.")
        except Exception as e:
            print("❌ Error creando usuario:", e)

# Verificamos nuevamente el balance
if minutos > 0:
    print("Hello! I am your AI English tutor...")
    nuevo_balance = restar_minuto_y_obtener_balance(phone)
    print(f"Minuto restado ✅ Nuevo balance: {nuevo_balance}")
else:
    print("No tienes minutos… por favor recarga.")
