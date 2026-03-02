import telnyx
import asyncio
from fastapi import FastAPI, Request, Response
from config import Config
from supabase_client import obtener_minutos, restar_minuto
from telnyx_sms import enviar_sms_recarga

app = FastAPI()
telnyx.api_key = Config.TELNYX_API_KEY

@app.post("/webhook")
async def handle_telnyx_call(request: Request):
    data = await request.json()
    payload = data['data']['payload']
    call_id = payload['call_control_id']
    from_number = payload['from']

    if data['data']['event_type'] == "call.initiated":
        if obtener_minutos(from_number) > 0:
            telnyx.Call.answer(call_id)
            # Saludo inicial
            telnyx.Call.speak(call_id, payload="Hello! I am your English tutor. How can I help you today?", voice="female", language="en-US")
            asyncio.create_task(control_tiempo(from_number, call_id))
        else:
            telnyx.Call.speak(call_id, payload="No tienes minutos. Revisa tu celular para recargar.", language="es-ES")
            enviar_sms_recarga(from_number)
            await asyncio.sleep(5)
            telnyx.Call.hangup(call_id)
    
    return Response(status_code=200)

async def control_tiempo(phone, call_id):
    while True:
        await asyncio.sleep(60)
        restar_minuto(phone)
        if obtener_minutos(phone) <= 0:
            telnyx.Call.speak(call_id, payload="Your time is up. Please recharge at our website. Goodbye!", language="en-US")
            await asyncio.sleep(4)
            telnyx.Call.hangup(call_id)
            break
