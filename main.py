import os
import uvicorn
import telnyx
import asyncio
from fastapi import FastAPI, Request, Response
from config import Config
from supabase_client import obtener_minutos, restar_minuto

app = FastAPI()

# Configuración de la API Key para versión 4.x
telnyx.api_key = Config.TELNYX_KEY

@app.get("/")
@app.head("/")
async def health():
    """Ruta para que Render siempre vea el servicio en VERDE"""
    return {"status": "online", "service": "AI English Tutor"}

@app.post("/webhook")
async def handle_webhook(request: Request):
    """Maneja las peticiones de Telnyx evitando los errores de tu imagen"""
    try:
        # Validación de cuerpo vacío para evitar error 'Expecting value'
        body = await request.body()
        if not body:
            return Response(content="OK", status_code=200)
        data = await request.json()
    except Exception as e:
        print(f"Petición ignorada (no es JSON válido): {e}")
        return Response(content="OK", status_code=200)

    try:
        payload = data.get('data', {}).get('payload', {})
        event_type = data.get('data', {}).get('event_type')
        call_control_id = payload.get('call_control_id')
        from_number = payload.get('from')

        if event_type == "call.initiated" and call_control_id:
            # 1. Consultar minutos en Supabase
            balance = obtener_minutos(from_number)
            
            if balance > 0:
                # SINTAXIS CORRECTA PARA TELNYX 4.59.0:
                telnyx.Call.answer(call_control_id)
                
                # Saludo inicial automático
                telnyx.Call.speak(
                    call_control_id,
                    payload="Hello! I'm your AI English tutor. How can I help you today?", 
                    voice="female", 
                    language="en-US"
                )
                # 2. Inicia el cronómetro de cobro cada 60 segundos
                asyncio.create_task(cronometro_cobro(from_number, call_control_id))
            else:
                # 3. Sin saldo: Avisar y colgar
                telnyx.Call.speak(call_control_id, payload="No tienes minutos. Por favor recarga.", language="es-ES")
                await asyncio.sleep(4)
                telnyx.Call.hangup(call_control_id)

    except Exception as e:
        print(f"Error procesando lógica de llamada: {e}")

    return Response(status_code=200)

async def cronometro_cobro(phone, call_id):
    """Descuenta 1 minuto cada 60 segundos de forma automática"""
    while True:
        await asyncio.sleep(60)
        restar_minuto(phone)
        if obtener_minutos(phone) <= 0:
            telnyx.Call.speak(call_id, payload="Your time is up. Please recharge. Goodbye!", language="en-US")
            await asyncio.sleep(3)
            telnyx.Call.hangup(call_id)
            break

if __name__ == "__main__":
    # Puerto por defecto para Render
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
