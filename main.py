import os
import uvicorn
import telnyx
import asyncio
from fastapi import FastAPI, Request, Response
from config import Config
from supabase_client import obtener_minutos, restar_minuto

app = FastAPI()

# Soporte para verificaciones de Render (Evita el error 405)
@app.get("/")
@app.head("/")
async def health_check():
    return {"status": "online", "tutor": "AI English"}

@app.post("/webhook")
async def handle_call(request: Request):
    telnyx.api_key = Config.TELNYX_KEY
    try:
        data = await request.json()
        payload = data.get('data', {}).get('payload', {})
        call_id = payload.get('call_control_id')
        from_number = payload.get('from')

        if data.get('data', {}).get('event_type') == "call.initiated":
            # Validamos minutos en Supabase
            saldo = obtener_minutos(from_number)
            if saldo > 0:
                telnyx.Call.answer(call_id)
                # Saludo inicial
                telnyx.Call.speak(call_id, payload="Hello! I'm your AI tutor. Let's practice English!", voice="female", language="en-US")
                # Iniciamos cobro automático cada 60 segundos
                asyncio.create_task(proceso_cobro(from_number, call_id))
            else:
                telnyx.Call.speak(call_id, payload="No tienes minutos. Recarga en nuestra web.", language="es-ES")
                await asyncio.sleep(4)
                telnyx.Call.hangup(call_id)
                
    except Exception as e:
        print(f"Error: {e}")
        
    return Response(status_code=200)

async def proceso_cobro(phone, call_id):
    while True:
        await asyncio.sleep(60)
        restar_minuto(phone)
        if obtener_minutos(phone) <= 0:
            telnyx.Call.speak(call_id, payload="Your time is up. Goodbye!", language="en-US")
            await asyncio.sleep(3)
            telnyx.Call.hangup(call_id)
            break

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=Config.PORT)
