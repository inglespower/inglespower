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

# Para que Telnyx pueda acceder a los archivos de audio que generamos
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

client = Telnyx(api_key=Config.TELNYX_API_KEY)
MI_URL_PUBLICA = "https://tu-app-en-render.onrender.com" # CAMBIA ESTO POR TU URL DE RENDER

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        event = data.get("data", {})
        payload = event.get("payload", {})
        call_id = payload.get("call_control_id")
        phone = payload.get("from")
        event_type = event.get("event_type")

        if event_type == "call.initiated":
            minutos = obtener_minutos(phone)
            if minutos > 0:
                client.calls.actions.answer(call_id)
            else:
                client.calls.actions.hangup(call_id)

        elif event_type == "call.answered":
            time.sleep(1.5) 
            hablar(call_id, "Welcome to your English practice. How can I help you?")

        elif event_type == "call.speak.ended" or event_type == "call.playback.ended":
            client.calls.actions.gather_using_ai(
                call_id, 
                parameters={"language": "en-US", "type": "chat_conversational"}
            )

        elif event_type == "call.gather.ended":
            transcripcion = payload.get("transcription")
            if transcripcion:
                respuesta_texto = generar_respuesta(transcripcion)
                hablar(call_id, respuesta_texto)
                restar_minuto(phone)
            else:
                hablar(call_id, "I didn't hear you. Please repeat.")

    except Exception as e:
        print(f"Error: {e}")
    return Response(status_code=200)

def hablar(call_id, texto):
    """Genera audio con ElevenLabs y le pide a Telnyx que lo reproduzca."""
    try:
        # 1. Crear el audio
        filename = f"static/audio_{int(time.time())}.mp3"
        archivo_generado = texto_a_voz(texto, filename)
        
        if archivo_generado:
            # 2. Pedirle a Telnyx que reproduzca la URL del audio
            audio_url = f"{MI_URL_PUBLICA}/{archivo_generado}"
            client.calls.actions.playback_start(call_id, audio_url=audio_url)
        else:
            # Fallback a voz robótica si ElevenLabs falla
            client.calls.actions.speak(call_id, payload=texto, voice="female", language="en-US")
    except Exception as e:
        print(f"Error al hablar: {e}")
