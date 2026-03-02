import os
import uvicorn
import telnyx
import asyncio
from fastapi import FastAPI, Request, Response
from config import Config
from supabase_client import obtener_minutos, restar_minuto
from telnyx_sms import enviar_sms_recarga

app = FastAPI()
telnyx.api_key = Config.TELNYX_API_KEY

@app.get("/")
async def health_check():
    return {"status": "online", "message": "Tutor de Inglés IA Activo"}

@app.post("/webhook")
async def handle_call(request: Request):
    data = await request.json()
    payload = data.get('data', {}).get('payload', {})
    call_id = payload.get('call_control_id')
    phone = payload.get('from')

    if data.get('data', {}).get('event_type') == "call.initiated":
        if obtener_minutos(phone) > 0:
            telnyx.Call.answer(call_id)
            telnyx.Call.speak(call_id, payload="Hello! I'm your English tutor. Let's practice!", voice="female", language="en-US")
            asyncio.create_task(cronometro_cobro(phone, call_id))
        else:
            telnyx.Call.speak(call_id, payload="No tienes minutos. Te enviamos un link de recarga.", language="es-ES")
            enviar_sms_recarga(phone)
            await asyncio.sleep(5)
            telnyx.Call.hangup(call_id)
    return Response(status_code=200)

async def cronometro_cobro(phone, call_id):
    while True:
        await asyncio.sleep(60)
        restar_minuto(phone)
        if obtener_minutos(phone) <= 0:
            telnyx.Call.speak(call_id, payload="Your minutes are over. Goodbye!", language="en-US")
            await asyncio.sleep(3)
            telnyx.Call.hangup(call_id)
            break

if __name__ == "__main__":
    # Render usa el puerto 10000 por defecto
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)

