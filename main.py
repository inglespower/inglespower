# main.py
from fastapi import FastAPI, Request
from supabase_client import conectar_db, obtener_minutos, restar_minuto_y_obtener_balance

app = FastAPI()

# Configuración inicial para usuarios nuevos
MINUTOS_INICIALES = 10

@app.post("/webhook")
async def webhook(request: Request):
    """
    Endpoint para recibir el número de teléfono desde un webhook.
    Devuelve mensaje según minutos disponibles.
    """
    try:
        data = await request.json()
    except Exception:
        return {"message": "Error: no se pudo leer el JSON del request."}

    phone = data.get("phone")
    if not phone:
        return {"message": "Error: no se recibió el teléfono."}

    db = conectar_db()
    if db is None:
        return {"message": "Error: no se pudo conectar a Supabase."}

    # Obtener minutos
    minutos = obtener_minutos(phone)

    # Si el usuario no existe o tiene 0 minutos, lo creamos con saldo inicial
    if minutos == 0:
        try:
            existing = db.table("users").select("*").eq("phone", phone).maybe_single().execute()
            if existing is None or not existing.data:
                db.table("users").insert({
                    "phone": phone,
                    "balance_minutes": MINUTOS_INICIALES
                }).execute()
                minutos = MINUTOS_INICIALES
        except Exception as e:
            return {"message": f"Error creando usuario: {e}"}

    # Responder según el balance
    if minutos > 0:
        nuevo_balance = restar_minuto_y_obtener_balance(phone)
        return {
            "message": "Hello! I am your AI English tutor...",
            "nuevo_balance": nuevo_balance
        }
    else:
        return {"message": "No tienes minutos… por favor recarga."}
