import time
import os
import telnyx
from telnyx import Telnyx
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from config import Config
from supabase_client import obtener_minutos, restar_minuto
from ai import generar_respuesta, texto_a_voz

app = FastAPI()

# Carpeta para audios temporales
if not os.path.exists("static"):
    os.makedirs("static")

app.mount("/static", StaticFiles(directory="static"), name="static")

# Configuración Telnyx v4
client = Telnyx(api_key=Config.TELNYX_API_KEY)
MI_URL_RENDER = "https://inglespower.onrender.com"

@app.get("/")
async def health():
    return {"status": "online", "service": "InglesPower AI Full"}

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        event = data.get("data", {})
        payload = event.get("payload", {})
        call_id = payload.get("call_control_id")
        phone = payload.get("from")
        event_type = event.get("event_type")

        # 1. LLAMADA INICIADA
        if event_type == "call.initiated":
            minutos = obtener_minutos(phone)
            if minutos > 0:
                print(f"Llamada de {phone}. Saldo: {minutos}")
                client.calls.actions.answer(call_id)
            else:
                client.calls.actions.hangup(call_id)

        # 2. LLAMADA CONTESTADA
        elif event_type == "call.answered":
            time.sleep(1.5)
            hablar(call_id, "Welcome to your English practice. I am Rachel, your tutor. How can I help you?")

        # 3. ACTIVAR ESCUCHA (Corrección Error 422)
        elif event_type in ["call.speak.ended", "call.playback.ended"]:
            client.calls.actions.gather_using_ai(
                call_id, 
                parameters={
                    "language": "en-US",
                    "type": "object",
                    "properties": {
                        "user_response": {
                            "type": "string",
                            "description": "Transcripción de la voz del usuario"
                        }
                    },
                    "required": ["user_response"]
                }
            )

        # 4. PROCESAR LO QUE EL USUARIO DIJO
        elif event_type == "call.gather.ended":
            transcripcion = payload.get("transcription")
            if transcripcion:
                print(f"Usuario: {transcripcion}")
                respuesta_texto = generar_respuesta(transcripcion)
                hablar(call_id, respuesta_texto)
                restar_minuto(phone)
            else:
                hablar(call_id, "I'm sorry, I didn't hear you. Please repeat.")

    except Exception as e:
        print(f"Error en Webhook: {e}")

    return Response(status_code=200)

def hablar(call_id, texto):
    """Genera audio realista y lo reproduce."""
    try:
        filename = f"audio_{int(time.time())}.mp3"
        filepath = os.path.join("static", filename)
        
        archivo_generado = texto_a_voz(texto, filepath)
        
        if archivo_generado:
            audio_url = f"{MI_URL_RENDER}/static/{filename}"
            client.calls.actions.playback_start(call_id, audio_url=audio_url)
        else:
            # Fallback si ElevenLabs falla
            client.calls.actions.speak(call_id, payload=texto, voice="female", language="en-US")
    except Exception as e:
        print(f"Error al hablar: {e}")
