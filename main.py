import os
import uvicorn
import telnyx
import asyncio
from fastapi import FastAPI, Request, Response
from config import Config
from supabase_client import obtener_minutos, restar_minuto

app = FastAPI()
telnyx.api_key = Config.TELNYX_API_KEY

@app.get("/")
async def root():
    # Esta ruta sirve para que Render vea que el puerto está abierto
    return {"status": "online", "port": Config.PORT}

@app.post("/webhook")
async def handle_call(request: Request):
    try:
        data = await request.json()
        payload = data.get('data', {}).get('payload', {})
        call_id = payload.get('call_control_id')
        from_number = payload.get('from')

        if data.get('data', {}).get('event_type') == "call.initiated":
            if obtener_minutos(from_number) > 0:
                telnyx.Call.answer(call_id)
                telnyx.Call.speak(call_id, payload="Hello! Welcome to your AI Tutor.", voice="female", language="en-US")
                asyncio.create_task(ciclo_cobro(from_number, call_id))
            else:
                telnyx.Call.speak(call_id, payload="No tienes minutos. Recarga en nuestra web.", language="es-ES")
                await asyncio.sleep(5)
                telnyx.Call.hangup(call_id)
    except Exception as e:
        print(f"Error: {e}")
    
    return Response(status_code=200)

async def ciclo_cobro(phone, call_id):
    while True:
        await asyncio.sleep(60)
        restar_minuto(phone)
        if obtener_minutos(phone) <= 0:
            telnyx.Call.speak(call_id, payload="Your time is up. Goodbye!", language="en-US")
            await asyncio.sleep(3)
            telnyx.Call.hangup(call_id)
            break

if __name__ == "__main__":
    # Arranca el servidor en el puerto que Render exige (10000)
    uvicorn.run(app, host="0.0.0.0", port=Config.PORT)
