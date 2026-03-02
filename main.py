import os
import uvicorn
import telnyx
import asyncio
from fastapi import FastAPI, Request, Response
from config import Config
from supabase_client import obtener_minutos, restar_minuto

app = FastAPI()

# Configuración de Telnyx
telnyx.api_key = Config.TELNYX_KEY

@app.get("/")
@app.head("/")
async def health():
    """Ruta para que Render marque el servicio como Live"""
    return {"status": "online", "service": "AI English Tutor"}

@app.post("/webhook")
async def handle_webhook(request: Request):
    """Maneja las peticiones de Telnyx de forma segura"""
    try:
        # CORRECCIÓN CRÍTICA: Leemos el cuerpo crudo primero
        body = await request.body()
        if not body:
            return Response(content="Empty Body", status_code=200)
        
        # Intentamos parsear el JSON
        data = await request.json()
    except Exception as e:
        print(f"Error al leer JSON: {e}")
        # Respondemos 200 para que Telnyx no reintente peticiones basura
        return Response(content="Invalid JSON", status_code=200)

    # Procesamos la lógica solo si es una llamada iniciada
    try:
        payload = data.get('data', {}).get('payload', {})
        event_type = data.get('data', {}).get('event_type')
        call_id = payload.get('call_control_id')
        from_number = payload.get('from')

        if event_type == "call.initiated" and call_id:
            # 1. Verificar minutos en Supabase
            balance = obtener_minutos(from_number)
            
            if balance > 0:
                telnyx.Call.answer(call_id)
                # Saludo inicial
                telnyx.Call.speak(
                    call_id, 
                    payload="Hello! I'm your AI tutor. Let's practice English!", 
                    voice="female", 
                    language="en-US"
                )
                # 2. Iniciar el cobro de minutos en segundo plano
                asyncio.create_task(cronometro_cobro(from_number, call_id))
            else:
                # 3. Sin saldo: Avisar y colgar
                telnyx.Call.speak(call_id, payload="No tienes minutos. Por favor recarga.", language="es-ES")
                await asyncio.sleep(4)
                telnyx.Call.hangup(call_id)

    except Exception as e:
        print(f"Error procesando lógica de llamada: {e}")

    return Response(status_code=200)

async def cronometro_cobro(phone, call_id):
    """Resta 1 minuto cada 60 segundos mientras la llamada esté activa"""
    while True:
        await asyncio.sleep(60)
        restar_minuto(phone)
        if obtener_minutos(phone) <= 0:
            telnyx.Call.speak(call_id, payload="Your time is up. Goodbye!", language="en-US")
            await asyncio.sleep(3)
            telnyx.Call.hangup(call_id)
            break

if __name__ == "__main__":
    # Render usa el puerto 10000 por defecto
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
