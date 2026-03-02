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

if not os.path.exists("static"):
    os.makedirs("static")

app.mount("/static", StaticFiles(directory="static"), name="static")

client = Telnyx(api_key=Config.TELNYX_API_KEY)
MI_URL_RENDER = "https://inglespower.onrender.com"

# Control de estado para evitar duplicados
asistente_activo = {}

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
                asistente_activo[call_id] = False
            else:
                client.calls.actions.hangup(call_id)

        elif event_type == "call.answered":
            time.sleep(1.5)
            hablar(call_id, "Welcome to your English practice. How can I help you today?")

        elif event_type in ["call.speak.ended", "call.playback.ended"]:
            if not asistente_activo.get(call_id, False):
                asistente_activo[call_id] = True
                client.calls.actions.gather_using_ai(
                    call_id, 
                    parameters={
                        "language": "en-US",
                        "type": "object",
                        "properties": {
                            "user_input": {"type": "string", "description": "Response"}
                        },
                        "required": ["user_input"]
                    }
                )

        elif event_type == "call.gather.ended":
            asistente_activo[call_id] = False
            transcripcion = payload.get("transcription")
            if transcripcion:
                respuesta = generar_respuesta(transcripcion)
                hablar(call_id, respuesta)
                restar_minuto(phone)
            else:
                hablar(call_id, "I'm sorry, I didn't hear you.")

    except Exception as e:
        print(f"Error Webhook: {e}")
    return Response(status_code=200)

def hablar(call_id, texto):
    try:
        filename = f"audio_{int(time.time())}.mp3"
        filepath = os.path.join("static", filename)
        archivo_generado = texto_a_voz(texto, filepath)
        
        if archivo_generado:
            audio_url = f"{MI_URL_RENDER}/static/{filename}"
            client.calls.actions.playback_start(call_id, audio_url=audio_url)
        else:
            client.calls.actions.speak(call_id, payload=texto, voice="female", language="en-US")
    except Exception as e:
        print(f"Error hablar: {e}")
