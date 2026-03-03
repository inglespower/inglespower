import os
import time
import glob
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from telnyx import Telnyx
from config import Config
from supabase_client import obtener_minutos, restar_minuto
from ai import generar_respuesta
from elevenlabs.client import ElevenLabs 

app = FastAPI()

# Inicialización de ElevenLabs v2.x
client_elevenlabs = ElevenLabs(api_key=Config.ELEVENLABS_API_KEY)

# Tu ID de voz de Thorthugo
VOICE_ID = "WOY6pnQ1WCg0mrOZ54lM"

# Carpeta para audios temporales
if not os.path.exists("static"):
    os.makedirs("static")

app.mount("/static", StaticFiles(directory="static"), name="static")

# Inicialización de Telnyx
client = Telnyx(api_key=Config.TELNYX_API_KEY)
MI_URL_RENDER = "https://inglespower.onrender.com"

# Control de llamadas
asistente_activo = {}
MAX_MP3_FILES = 20

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        event = data.get("data", {})
        payload = event.get("payload", {})
        call_id = payload.get("call_control_id")
        phone = payload.get("from")
        event_type = event.get("event_type")

        print(f"[EVENTO] {event_type} | Call ID: {call_id}")

        if event_type == "call.initiated":
            minutos = obtener_minutos(phone)
            if minutos > 0:
                # Contestar la llamada
                client.calls.actions.answer(call_control_id=call_id)
                asistente_activo[call_id] = True
            else:
                client.calls.actions.hangup(call_control_id=call_id)

        elif event_type == "call.answered":
            time.sleep(1)
            hablar(call_id, "Hi! I'm Thorthugo, your English tutor. Ready to practice today?")

        elif event_type in ["call.speak.ended", "call.audio_playback.ended"]:
            if asistente_activo.get(call_id, False):
                try:
                    # Escuchar al usuario
                    client.calls.actions.gather_using_ai(
                        call_control_id=call_id,
                        parameters={
                            "language": "en-US",
                            "type": "object",
                            "properties": {"user_input": {"type": "string"}},
                            "required": ["user_input"]
                        }
                    )
                except Exception as e:
                    print(f"[ERROR GATHER] {e}")

        elif event_type == "call.gather.ended":
            transcripcion = payload.get("transcription")
            if transcripcion:
                respuesta = generar_respuesta(transcripcion)
                restar_minuto(phone)
                hablar(call_id, respuesta)
            else:
                hablar(call_id, "I'm sorry, I didn't hear you. Could you please repeat?")

        elif event_type == "call.hangup":
            asistente_activo.pop(call_id, None)

    except Exception as e:
        print(f"[ERROR Webhook] {e}")
    return Response(status_code=200)

def hablar(call_id, texto):
    if not asistente_activo.get(call_id, False):
        return

    try:
        # 1. Generar audio con ElevenLabs (Método Robusto v2)
        audio_stream = client_elevenlabs.text_to_speech.convert(
            voice_id=VOICE_ID,
            text=texto,
            model_id="eleven_multilingual_v2"
        )
        audio_bytes = b"".join(audio_stream)

        # 2. Guardar archivo local
        timestamp = int(time.time() * 1000)
        filename = f"audio_{timestamp}.mp3"
        filepath = os.path.join("static", filename)
        with open(filepath, "wb") as f:
            f.write(audio_bytes)

        limpiar_archivos_mp3()
        audio_url = f"{MI_URL_RENDER}/static/{filename}"

        # 3. CORRECCIÓN TELNYX: Recuperar objeto de llamada y reproducir
        # Esta es la forma correcta de usar playback_start en la SDK de Python
        try:
            # Primero obtenemos el control de la llamada activa
            call = client.calls.retrieve(call_id)
            # Luego ejecutamos la acción sobre ese objeto
            call.playback_start(audio_url=audio_url)
            print(f"[EXITO] Reproduciendo en llamada {call_id}: {audio_url}")
        except Exception as e:
            print(f"[ERROR Telnyx Playback] {e}")

    except Exception as e:
        print(f"[ERROR CRÍTICO HABLAR] {e}")

def limpiar_archivos_mp3():
    files = sorted(glob.glob("static/audio_*.mp3"), key=os.path.getmtime)
    if len(files) > MAX_MP3_FILES:
        for f in files[:-MAX_MP3_FILES]:
            try:
                os.remove(f)
            except:
                pass
