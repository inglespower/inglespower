import time
import os
import base64
from telnyx import Telnyx
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from config import Config
from supabase_client import obtener_minutos, restar_minuto
from ai import generar_respuesta
from elevenlabs import generate, set_api_key

app = FastAPI()

# Inicializar ElevenLabs
set_api_key(Config.ELEVENLABS_API_KEY)

# Crear carpeta static
if not os.path.exists("static"):
    os.makedirs("static")

app.mount("/static", StaticFiles(directory="static"), name="static")

# Telnyx cliente
client = Telnyx(api_key=Config.TELNYX_API_KEY)
MI_URL_RENDER = "https://inglespower.onrender.com"

# Control de estado por llamada
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

        print("Evento recibido:", event_type)

        # 1️⃣ Llamada iniciada
        if event_type == "call.initiated":
            minutos = obtener_minutos(phone)
            if minutos > 0:
                client.calls.actions.answer(call_control_id=call_id)
                asistente_activo[call_id] = False
            else:
                client.calls.actions.hangup(call_control_id=call_id)

        # 2️⃣ Llamada contestada
        elif event_type == "call.answered":
            time.sleep(1)
            hablar(call_id, "Hola, soy Thorthugo, tu tutor de inglés. ¿Qué quieres practicar hoy?")

        # 3️⃣ Cuando termina de hablar
        elif event_type in ["call.speak.ended"]:
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

        # 4️⃣ Cuando termina el gather
        elif event_type == "call.gather.ended":
            asistente_activo[call_id] = False
            transcripcion = payload.get("transcription")
            if transcripcion:
                respuesta = generar_respuesta(transcripcion)
                hablar(call_id, respuesta)
                restar_minuto(phone)
            else:
                hablar(call_id, "No te escuché bien. ¿Podrías repetir?")

        # 5️⃣ Cuando se cuelga
        elif event_type == "call.hangup":
            asistente_activo.pop(call_id, None)

    except Exception as e:
        print("Error Webhook:", e)

    return Response(status_code=200)


def hablar(call_id, texto):
    try:
        # Generar audio con ElevenLabs
        audio = generate(
            text=texto,
            voice="alloy",  # Cambia a tu voz de ElevenLabs
            model="eleven_multilingual_v1"
        )
        
        # Guardar archivo temporal
        timestamp = int(time.time())
        filename = f"audio_{timestamp}.mp3"
        filepath = os.path.join("static", filename)
        with open(filepath, "wb") as f:
            f.write(audio)

        # Usar URL público de Render para reproducir
        audio_url = f"{MI_URL_RENDER}/static/{filename}"
        client.calls.actions.speak(
            call_control_id=call_id,
            payload=texto,      # fallback TTS de Telnyx
            voice="female",
            language="es-MX"
        )

    except Exception as e:
        print("Error hablar:", e)
