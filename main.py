import time
import os
from telnyx import Telnyx
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from config import Config
from supabase_client import obtener_minutos, restar_minuto
from ai import generar_respuesta, texto_a_voz

app = FastAPI()

# Crear carpeta static si no existe
if not os.path.exists("static"):
    os.makedirs("static")

app.mount("/static", StaticFiles(directory="static"), name="static")

# Cliente Telnyx
client = Telnyx(api_key=Config.TELNYX_API_KEY)

MI_URL_RENDER = "https://inglespower.onrender.com"

# Estado por llamada
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

        print("Evento:", event_type)

        # Cuando inicia la llamada
        if event_type == "call.initiated":
            minutos = obtener_minutos(phone)

            if minutos > 0:
                client.calls.actions.answer(call_control_id=call_id)
                asistente_activo[call_id] = False
            else:
                client.calls.actions.hangup(call_control_id=call_id)

        # Cuando la llamada es contestada
        elif event_type == "call.answered":
            time.sleep(1.5)
            hablar(call_id, "Hola, soy Thorthugo, tu tutor de inglés. ¿Qué quieres practicar hoy?")

        # Cuando termina de hablar o reproducir audio
        elif event_type in ["call.speak.ended", "call.playback.ended"]:
            if not asistente_activo.get(call_id, False):
                asistente_activo[call_id] = True

                client.calls.actions.gather_using_ai(
                    call_control_id=call_id,
                    parameters={
                        "language": "es-MX",
                        "type": "object",
                        "properties": {
                            "user_input": {
                                "type": "string",
                                "description": "Respuesta del usuario"
                            }
                        },
                        "required": ["user_input"]
                    }
                )

        # Cuando termina el gather
        elif event_type == "call.gather.ended":
            asistente_activo[call_id] = False
            transcripcion = payload.get("transcription")

            if transcripcion:
                respuesta = generar_respuesta(transcripcion)
                hablar(call_id, respuesta)
                restar_minuto(phone)
            else:
                hablar(call_id, "No te escuché bien. ¿Podrías repetir?")

        # Cuando se cuelga
        elif event_type == "call.hangup":
            asistente_activo.pop(call_id, None)

    except Exception as e:
        print("Error Webhook:", e)

    return Response(status_code=200)


def hablar(call_id, texto):
    try:
        filename = f"audio_{int(time.time())}.mp3"
        filepath = os.path.join("static", filename)

        archivo_generado = texto_a_voz(texto, filepath)

        if archivo_generado:
            audio_url = f"{MI_URL_RENDER}/static/{filename}"

            client.calls.actions.audio_playback_start(
                call_control_id=call_id,
                audio_url=audio_url
            )
        else:
            client.calls.actions.speak(
                call_control_id=call_id,
                payload=texto,
                voice="female",
                language="es-MX"
            )

    except Exception as e:
        print("Error hablar:", e)
