# main.py
from fastapi import FastAPI, Request
from supabase_client import conectar_db, obtener_minutos, restar_minuto_y_obtener_balance
import re

app = FastAPI()

MINUTOS_INICIALES = 10
PHONE_REGEX = re.compile(r"^\+\d{10,15}$")  # Formato internacional +15555555555

@app.post("/webhook")
async def telnyx_call_webhook(request: Request):
    """
    Endpoint para manejar llamadas Telnyx.
    Devuelve acciones TTS según los minutos disponibles.
    """
    try:
        data = await request.json()
    except Exception:
        return {"actions": [{"say": {"payload": "Error leyendo datos de la llamada."}}]}

    phone = data.get("from")
    if not phone:
        return {"actions": [{"say": {"payload": "No se recibió número de teléfono."}}]}

    if not PHONE_REGEX.match(phone):
        return {"actions": [{"say": {"payload": "Número de teléfono inválido."}}]}

    db = conectar_db()
    if db is None:
        return {"actions": [{"say": {"payload": "Error de conexión a la base de datos."}}]}

    # Obtener minutos
    minutos = obtener_minutos(phone)

    # Crear usuario si no existe
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
            return {"actions": [{"say": {"payload": f"Error creando usuario: {e}"}}]}

    # Preparar acción de Telnyx
    response_actions = []

    if minutos > 0:
        # Restar un minuto
        nuevo_balance = restar_minuto_y_obtener_balance(phone)
        response_actions.append({
            "say": {
                "payload": "Hello! I am your AI English tutor.",
                "voice": "alloy",
                "language": "en-US"
            }
        })
    else:
        response_actions.append({
            "say": {
                "payload": "No tienes minutos, por favor recarga.",
                "voice": "alloy",
                "language": "en-US"
            }
        })

    return {"actions": response_actions}
