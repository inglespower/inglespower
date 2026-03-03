import os
import time
import glob
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
import telnyx
from config import Config
from supabase_client import obtener_minutos, restar_minuto
from ai import generar_respuesta
from elevenlabs.client import ElevenLabs 

app = FastAPI()

# 1. Cliente ElevenLabs (Voz Real)
el_client = ElevenLabs(api_key=Config.ELEVENLABS_API_KEY)
VOICE_ID = "WOY6pnQ1WCg0mrOZ54lM"

# 2. Cliente Telnyx v4.0.0 (Sintaxis Actualizada)
telnyx_client = telnyx.Telnyx(api_key=Config.TELNYX_API_KEY)
MI_URL_RENDER = "https://inglespower.onrender.com"

# Carpeta static
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

asistente_activo = {}
MAX_MP3_FILES = 15

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        event_data = data.get("data", {})
        payload = event_data.get("payload", {})
        event_type = event_data.get("event_type")
        call_id = payload.get("call_control_id")
        phone = payload.get("from")

        if not call_id: return Response(status_code=200)

        print(f"[EVENTO] {event_type} | ID: {call_id}")

        if event_type == "call.initiated":
            minutos = obtener_minutos(phone)
            if minutos > 0:
                # SINTAXIS V4: Acceso vía calls.call_control.answer
                telnyx_client.calls.call_control.answer(call_id)
                asistente_activo[call_id] = True
            else:
                telnyx_client.calls.call_control.hangup(call_id)

        elif event_type == "call.answered":
            time.sleep(1)
            hablar(call_id, "Hola, soy Thorthugo. ¿Qué quieres practicar hoy?")

        elif event_type in ["call.speak.ended", "call.audio_playback.ended"]:
            if asistente_activo.get(call_id):
                # SINTAXIS V4: Acceso vía calls.call_control.gather_using_ai
                telnyx_client.calls.call_control.gather_using_ai(
                    call_id,
                    language="es-MX",
                    parameters={
                        "type": "object",
                        "properties": {"user_input": {"type": "string"}},
                        "required": ["user_input"]
                    }
                )

        elif event_type == "call.gather.ended":
            transcripcion = payload.get("transcription")
            if transcripcion:
                respuesta = generar_respuesta(transcripcion)
                restar_minuto(phone)
                hablar(call_id, respuesta)

        elif event_type == "call.hangup":
            asistente_activo.pop(call_id, None)

    except Exception as e:
        print(f"[ERROR WEBHOOK] {e}")
    return Response(status_code=200)

def hablar(call_id, texto):
    if not asistente_activo.get(call_id): return

    try:
        # ElevenLabs v2
        audio_iterator = el_client.text_to_speech.convert(
            voice_id=VOICE_ID,
            text=texto,
            model_id="eleven_multilingual_v2"
        )
        audio_bytes = b"".join(audio_iterator)

        filename = f"audio_{int(time.time()*1000)}.mp3"
        filepath = os.path.join("static", filename)
        with open(filepath, "wb") as f:
            f.write(audio_bytes)

        limpiar_archivos_mp3()
        audio_url = f"{MI_URL_RENDER}/static/{filename}"

        # SINTAXIS V4: Acceso vía calls.call_control.playback_start
        telnyx_client.calls.call_control.playback_start(
            call_id,
            audio_url=audio_url
        )
        print(f"[OK] Reproduciendo: {filename}")

    except Exception as e:
        print(f"[ERROR HABLAR] {e}")

def limpiar_archivos_mp3():
    files = sorted(glob.glob("static/audio_*.mp3"), key=os.path.getmtime)
    if len(files) > MAX_MP3_FILES:
        for f in files[:-MAX_MP3_FILES]:
            try: os.remove(f)
            except: pass
