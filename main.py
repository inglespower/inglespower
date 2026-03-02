import os
from fastapi import FastAPI, Request, Response
import telnyx
from supabase_client import supabase
from ai import obtener_respuesta_ai

app = FastAPI()
telnyx.api_key = os.getenv("TELNYX_API_KEY")

@app.get("/")
async def root():
    return {"status": "online", "message": "Servidor de Voz AI Activo"}

@app.post("/webhook")
async def handle_call(request: Request):
    data = await request.json()
    event = data.get("data", {})
    payload = event.get("payload", {})
    call_control_id = payload.get("call_control_id")
    
    # 1. Identificar al cliente por su número de teléfono
    from_number = payload.get("from")
    
    if event.get("event_type") == "call.initiated":
        # Verificar saldo en Supabase
        user = supabase.table("users").select("minutes_balance").eq("phone", from_number).single().execute()
        
        if user.data and user.data["minutes_balance"] > 0:
            telnyx.Call.answer(call_control_id=call_control_id)
            enviar_texto_a_voz(call_control_id, "Hola, bienvenido. ¿En qué puedo ayudarte hoy?")
        else:
            telnyx.Call.answer(call_control_id=call_control_id)
            enviar_texto_a_voz(call_control_id, "Lo siento, no tienes minutos suficientes. Por favor recarga en nuestra web.")
            telnyx.Call.hangup(call_control_id=call_control_id)

    return Response(status_code=200)

def enviar_texto_a_voz(call_id, texto):
    telnyx.Call.speak(
        call_control_id=call_id,
        payload=texto,
        voice="female",
        language="es-ES"
    )
