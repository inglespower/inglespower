import os
import time
import glob
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from telnyx import Telnyx
from config import Config
from supabase_client import obtener_minutos, restar_minuto
from ai import generar_respuesta
from elevenlabs.client import ElevenLabs  # Importación oficial v2.x

app = FastAPI()

# Inicializar ElevenLabs con tu API KEY de Config
client_elevenlabs = ElevenLabs(api_key=Config.ELEVENLABS_API_KEY)

# ID de tu voz personalizada Thorthugo
VOICE_ID = "WOY6pnQ1WCg0mrOZ54lM"

# Carpeta static para archivos temporales
if not os.path.exists("static"):
    os.makedirs("static")

app.mount("/static", StaticFiles(directory="static"), name="static")

# Configuración Telnyx
client = Telnyx(api_key=Config.TELNYX_API_KEY)
MI_URL_RENDER = "https://inglespower.onrender.com"

# Control de llamadas activas
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

        print(f"[EVENTO] {event_type} | Call ID: {call_id} | Teléfono: {phone}")

        if event_type == "call.initiated":
            minutos = obtener_minutos(phone)
            if minutos > 0:
                client.calls.actions.answer(call_control_id=call_id)
                asistente_activo[call_id] = True
                print(f"[MINUTOS DISPONIBLES] {minutos} para {phone}")
            else:
                client.calls.actions.hangup(call_control_id=call_id)

        elif event_type == "call.answered":
            time.sleep(1)
            hablar(call_id, "Hi! I'm Thorthugo, your English tutor. What would you like to practice today?")

        elif event_type in ["call.speak.ended", "call.audio_playback.ended"]:
            if asistente_activo.get(call_id, False):
                try:
                    client.calls.actions.gather_using_ai(
                        call_control_id=call_id,
                        parameters={
                            "language": "en-US", # Cambiado a inglés para mejor detección del tutor
                            "type": "object",
                            "properties": {
                                "user_input": {"type": "string", "description": "User's English response"}
                            },
                            "required": ["user_input"]
                        }
                    )
                except Exception as e:
                    if "90018" in str(e):
                        print(f"[CALL YA TERMINADA] Call ID: {call_id}")
                    else:
                        print(f"[ERROR GATHER] {e}")

        elif event_type == "call.gather.ended":
            transcripcion = payload.get("transcription")
            if transcripcion:
                respuesta = generar_respuesta(transcripcion)
                restar_minuto(phone)
                hablar(call_id, respuesta)
            else:
                hablar(call_id, "I'm sorry, I didn't catch that. Could you repeat please?")

        elif event_type == "call.hangup":
            asistente_activo.pop(call_id, None)
            print(f"[HANGUP] Llamada finalizada: {call_id}")

    except Exception as e:
        print(f"[ERROR Webhook] {e}")

    return Response(status_code=200)


def hablar(call_id, texto):
    if not asistente_activo.get(call_id, False):
        print(f"[INFO] Call ID {call_id} no está activa, cancelando audio")
        return

    try:
        # Generar audio usando el generador de ElevenLabs v2
        audio_generator = client_elevenlabs.generate(
            text=texto,
            voice=VOICE_ID, 
            model="eleven_multilingual_v2"
        )
        
        # Unir los chunks del generador en un solo bloque de bytes
        audio_bytes = b"".join(audio_generator)

        # Crear nombre de archivo único con milisegundos
        timestamp = int(time.time() * 1000)
        filename = f"audio_{timestamp}.mp3"
        filepath = os.path.join("static", filename)
        
        with open(filepath, "wb") as f:
            f.write(audio_bytes)

        limpiar_archivos_mp3()

        # URL final para Telnyx
        audio_url = f"{MI_URL_RENDER}/static/{filename}"

        # Iniciar reproducción en la llamada
        try:
            client.calls.actions.audio_playback_start(
                call_control_id=call_id,
                audio_url=audio_url
            )
            print(f"[PLAYBACK START] Thorthugo dice: {texto[:50]}...")
        except Exception as e:
            if "90018" in str(e):
                print(f"[CALL YA TERMINADA] No se pudo reproducir audio")
            else:
                print(f"[ERROR Playback] {e}")

    except Exception as e:
        print(f"[ERROR ElevenLabs Hablar] {e}")


def limpiar_archivos_mp3():
    files = sorted(glob.glob("static/audio_*.mp3"), key=os.path.getmtime)
    if len(files) > MAX_MP3_FILES:
        for f in files[:-MAX_MP3_FILES]:
            try:
                os.remove(f)
                print(f"[CLEANUP] Borrado: {f}")
            except:
                pass
