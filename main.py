import telnyx
import asyncio
from fastapi import FastAPI, Request, Response
from config import Config
from supabase_client import obtener_minutos, restar_minuto
from telnyx_sms import enviar_sms_recarga

app = FastAPI()
telnyx.api_key = Config.TELNYX_API_KEY

@app.post("/webhook")
async def handle_call(request: Request):
    data = await request.json()
    payload = data['data']['payload']
    call_id = payload['call_control_id']
    phone = payload['from']

    if data['data']['event_type'] == "call.initiated":
        # 1. Verificar minutos disponibles
        balance = obtener_minutos(phone)
        
        if balance > 0:
            telnyx.Call.answer(call_id)
            # Saludo inicial automático
            telnyx.Call.speak(
                call_id, 
                payload="Hello! I'm your English tutor. Let's practice!", 
                voice="female", 
                language="en-US"
            )
            # 2. Inicia el cobro automático cada 60 segundos en segundo plano
            asyncio.create_task(cronometro_cobro(phone, call_id))
        else:
            # 3. Si no hay saldo, avisar y enviar link de Replit por SMS
            telnyx.Call.speak(call_id, payload="No tienes minutos. Te enviamos un link de recarga.", language="es-ES")
            enviar_sms_recarga(phone)
            await asyncio.sleep(5)
            telnyx.Call.hangup(call_id)
            
    return Response(status_code=200)

async def cronometro_cobro(phone, call_id):
    """Descuenta 1 minuto de Supabase cada 60 segundos de llamada"""
    while True:
        await asyncio.sleep(60)
        restar_minuto(phone)
        # Verificar si se quedó sin minutos durante la llamada
        if obtener_minutos(phone) <= 0:
            telnyx.Call.speak(call_id, payload="Your minutes are over. Please recharge. Goodbye!", language="en-US")
            await asyncio.sleep(4)
            telnyx.Call.hangup(call_id)
            break
