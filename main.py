import os
import uvicorn
import telnyx
import asyncio
from fastapi import FastAPI, Request, Response
from config import Config
from supabase_client import obtener_minutos, restar_minuto

app = FastAPI()

# Configuración obligatoria de la API Key
telnyx.api_key = Config.TELNYX_KEY

@app.get("/")
@app.head("/")
async def health():
    return {"status": "online", "tutor": "AI English Ready"}

@app.post("/webhook")
async def handle_webhook(request: Request):
    try:
        body = await request.body()
        if not body: return Response(content="OK", status_code=200)
        data = await request.json()
        
        payload = data.get('data', {}).get('payload', {})
        event_type = data.get('data', {}).get('event_type')
        call_control_id = payload.get('call_control_id')
        from_number = payload.get('from')

        if event_type == "call.initiated" and call_control_id:
            # 1. Verificar minutos antes de contestar
            if obtener_minutos(from_number) > 0:
                # CORRECCIÓN PARA EL ERROR: Nueva forma de llamar a Telnyx
                call = telnyx.Call(call_control_id=call_control_id)
                call.answer()
                
                # Saludo inicial
                call.speak(
                    payload="Hello! I'm your AI tutor. Let's practice English!", 
                    voice="female", 
                    language="en-US"
                )
                
                # 2. Iniciar cobro automático cada 60 segundos
                asyncio.create_task(cronometro_cobro(from_number, call_control_id))
            else:
                # Sin saldo: Avisar y colgar
                call = telnyx.Call(call_control_id=call_control_id)
                call.speak(payload="No tienes minutos. Recarga en nuestra web.", language="es-ES")
                await asyncio.sleep(4)
                call.hangup()
    except Exception as e:
        print(f"Error procesando lógica de llamada: {e}")
        
    return Response(status_code=200)

async def cronometro_cobro(phone, call_id):
    while True:
        await asyncio.sleep(60)
        restar_minuto(phone)
        if obtener_minutos(phone) <= 0:
            call = telnyx.Call(call_control_id=call_id)
            call.speak(payload="Your time is up. Goodbye!", language="en-US")
            await asyncio.sleep(3)
            call.hangup()
            break

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
