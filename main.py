import os
import time
import glob
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from telnyx import Telnyx
from config import Config
from supabase_client import obtener_minutos, restar_minuto
from ai import generar_respuesta
# --- CORRECCIÓN CRÍTICA DE IMPORTACIÓN ---
from elevenlabs.client import ElevenLabs 

app = FastAPI()

# Inicializar ElevenLabs v2.x correctamente
client_elevenlabs = ElevenLabs(api_key=Config.ELEVENLABS_API_KEY)

# Tu ID de voz de Thorthugo
VOICE_ID = "WOY6pnQ1WCg0mrOZ54lM"

# Carpeta para archivos de audio temporales
if not os.path.exists("static"):
    os.makedirs("static")

app.mount("/static", StaticFiles(directory="static"), name="static")

# Configuración de Telnyx
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
            # Thorthugo saluda primero al contestar
            time.sleep(1)
            hablar(call_id, "Hi! I'm Thorthugo, your English tutor. What would you like to practice today?")

        elif event_type in ["call.speak.ended", "call.audio_playback.ended"]:
            if asistente_activo.get(call_id, False):
                try:
                    # Escuchar al usuario después de que Thorthugo termina de hablar
                    client.calls.actions.gather_using_ai(
                        call_control_id=call_id,
                        parameters={
                            "language": "en-US",
                            "type": "object",
                            "properties": {
                                "user_input": {"type": "string", "description": "Respuesta del usuario"}
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
                # Generar respuesta de la IA (Thorthugo)
                respuesta = generar_respuesta(transcripcion)
                restar_minuto(phone)
                hablar(call_id, respuesta)
            else:
                hablar(call_id, "I'm sorry, I didn't hear you clearly. Could you repeat that?")

        elif event_type == "call.hangup":
            asistente_activo.pop(call_id, None)
            print(f"[HANGUP] Llamada finalizada: {call_id}")

    except Exception as e:
        print(f"[ERROR Webhook] {e}")

    return Response(status_code=200)


def hablar(call_id, texto):
    if not asistente_activo.get(call_id, False):
        print(f"[INFO] Call ID {call_id} inactiva. No se genera audio.")
        return

    try:
        # --- GENERACIÓN DE AUDIO CORREGIDA PARA V2.X ---
        # El método .generate del cliente devuelve un iterador de bytes
        audio_generator = client_elevenlabs.generate(
            text=texto,
            voice=VOICE_ID,
            model="eleven_multilingual_v2" # Mejor modelo para inglés/español
        )
        
        # Unimos los fragmentos (chunks) en un solo objeto de bytes
        audio_bytes = b"".join(audio_generator)

        # Guardar el archivo MP3 con nombre único
        timestamp = int(time.time() * 1000)
        filename = f"audio_{timestamp}.mp3"
        filepath = os.path.join("static", filename)
        
        with open(filepath, "wb") as f:
            f.write(audio_bytes)

        # Limpieza automática de archivos viejos
        limpiar_archivos_mp3()

        # URL que Telnyx descargará para reproducir en la llamada
        audio_url = f"{MI_URL_RENDER}/static/{filename}"

        # Iniciar reproducción en la llamada de Telnyx
        try:
            client.calls.actions.audio_playback_start(
                call_control_id=call_id,
                audio_url=audio_url
            )
            print(f"[PLAYBACK] Thorthugo enviando audio: {filename}")
        except Exception as e:
            if "90018" in str(e):
                print(f"[INFO] La llamada se cerró antes de reproducir audio.")
            else:
                print(f"[ERROR Playback] {e}")

    except Exception as e:
        # Aquí capturamos el error que veías en los logs
        print(f"[ERROR ElevenLabs Hablar] {e}")


def limpiar_archivos_mp3():
    files = sorted(glob.glob("static/audio_*.mp3"), key=os.path.getmtime)
    if len(files) > MAX_MP3_FILES:
        for f in files[:-MAX_MP3_FILES]:
            try:
                os.remove(f)
                print(f"[BORRADO] Archivo antiguo: {f}")
            except:
                pass
