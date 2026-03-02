import time
import telnyx
from telnyx import Telnyx
from fastapi import FastAPI, Request, Response
from config import Config
from supabase_client import obtener_minutos, restar_minuto
from ai import generar_respuesta

app = FastAPI()

# Inicialización correcta para Telnyx v4+
client = Telnyx(api_key=Config.TELNYX_API_KEY)

@app.get("/")
async def health():
    return {"status": "online", "service": "InglesPower AI"}

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        event = data.get("data", {})
        payload = event.get("payload", {})
        call_id = payload.get("call_control_id")
        phone = payload.get("from")
        event_type = event.get("event_type")

        # 1. LLAMADA INICIADA: Validar saldo y contestar
        if event_type == "call.initiated":
            minutos = obtener_minutos(phone)
            if minutos > 0:
                print(f"Llamada de {phone}. Minutos: {minutos}. Contestando...")
                client.calls.actions.answer(call_id)
            else:
                print(f"Sin saldo para {phone}. Colgando.")
                client.calls.actions.hangup(call_id)

        # 2. LLAMADA CONTESTADA: Saludo inicial con delay de audio
        elif event_type == "call.answered":
            time.sleep(1.5) 
            hablar(call_id, "Welcome to your English practice. How can I help you today?")

        # 3. FIN DE AUDIO DE IA: Activar escucha (Gather con IA)
        elif event_type == "call.speak.ended":
            # CORRECCIÓN DEFINITIVA PARA ERROR 422:
            # Telnyx v4 requiere 'parameters' con estructura de esquema (properties).
            client.calls.actions.gather_using_ai(
                call_id, 
                parameters={
                    "language": "en-US",
                    "voice_model": "telnyx_voice_en_us_1"
                }
            )

        # 4. USUARIO TERMINA DE HABLAR: Procesar respuesta con OpenAI
        elif event_type == "call.gather.ended":
            # En v4 la transcripción suele venir dentro de 'transcription' en el payload
            transcripcion = payload.get("transcription")
            
            if transcripcion:
                print(f"Usuario dijo: {transcripcion}")
                respuesta = generar_respuesta(transcripcion)
                hablar(call_id, respuesta)
                restar_minuto(phone) # Descontamos 1 minuto en Supabase
            else:
                print("No se detectó transcripción, pidiendo repetir...")
                hablar(call_id, "I'm sorry, I didn't hear you. Could you repeat that?")

    except Exception as e:
        # Esto nos dirá en el log de Render exactamente qué línea falla ahora
        print(f"Error detectado en Webhook: {e}")

    return Response(status_code=200)

def hablar(call_id, texto):
    """Función para enviar comandos de voz usando la sintaxis V4."""
    try:
        client.calls.actions.speak(
            call_id,
            payload=texto,
            voice="female",
            language="en-US"
        )
    except Exception as e:
        print(f"Error al ejecutar speak: {e}")
