import os
import uvicorn
import telnyx
import asyncio
from fastapi import FastAPI, Request, Response
from config import Config
from supabase_client import obtener_minutos, restar_minuto

# IMPORTACIÓN DIRECTA PARA EVITAR EL ERROR DE ATRIBUTO
from telnyx.api_resources.call import Call

app = FastAPI()
telnyx.api_key = Config.TELNYX_KEY

@app.get("/")
@app.head("/")
async def health():
    return {"status": "online"}

@app.post("/webhook")
async def handle_webhook(request: Request):
    try:
        body = await request.body()
        if not body:
            return Response(content="OK", status_code=200)
        data = await request.json()
        
        payload = data.get('data', {}).get('payload', {})
        event_type = data.get('data', {}).get('event_type')
        call_id = payload.get('call_control_id')
        from_number = payload.get('from')

        if event_type == "call.initiated" and call_id:
            balance = obtener_minutos(from_number)
            if balance > 0:
                # USAMOS LA CLAVE IMPORTADA DIRECTAMENTE
                Call.answer(call_id)
                
                # Saludo inicial
                Call.speak(
                    call_id, 
                    payload="Hello! I am your AI English tutor. How can I help you today?", 
                    voice="female", 
                    language="en-US"
                )
                asyncio.create_task(cronometro_cobro(from_number, call_id))
            else:
                Call.speak(call_id, payload="No tienes minutos. Por favor recarga.", language="es-ES")
                await asyncio.sleep(4)
                Call.hangup(call_id)
    except Exception as e:
        print(f"Error procesando lógica de llamada: {e}")
        
    return Response(status_code=200)

async def cronometro_cobro(phone, call_id):
    while True:
        await asyncio.sleep(60)
        restar_minuto(phone)
        if obtener_minutos(phone) <= 0:
            Call.speak(call_id, payload="Your time is up. Goodbye!", language="en-US")
            await asyncio.sleep(3)
            Call.hangup(call_id)
            break

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
``` [1.1]
