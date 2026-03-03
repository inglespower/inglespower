import time
import os
import glob
from telnyx import Telnyx
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from config import Config
from supabase_client import obtener_minutos, restar_minuto
from ai import generar_respuesta
from elevenlabs import generate, set_api_key  # versión 1.0.0

app = FastAPI()

# Inicializar ElevenLabs
set_api_key(Config.ELEVENLABS_API_KEY)

# Crear carpeta static si no existe
if not os.path.exists("static"):
    os.makedirs("static")

app.mount("/static", StaticFiles(directory="static"), name="static")

# Telnyx cliente
client = Telnyx(api_key=Config.TELNYX_API_KEY)
MI_URL_RENDER = "https://inglespower.onrender.com"

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
            print(f"[MINUTOS DISPONIBLES] {minutos} para {phone}")
            if minutos > 0:
                client.calls.actions.answer(call_control_id=call_id)
                asistente_activo[call_id] = False
            else:
                client.calls.actions.hangup(call_control_id=call_id)
                print(f"[HANGUP] Usuario sin minutos: {phone}")

        elif event_type == "call.answered":
            time.sleep(1)
            hablar(call_id, "Hola, soy Thorthugo, tu tutor de inglés. ¿Qué quieres practicar hoy?")

        elif event_type in ["call.speak.ended", "call.audio_playback.ended"]:
            if not asistente_activo.get(call_id, False):
                asistente_activo[call_id] = True
                client.calls.actions.gather_using_ai(
                    call_control_id=call_id,
                    parameters={
                        "language": "es-MX",
                        "type": "object",
                        "properties": {
                            "user_input": {"type": "string", "description": "Respuesta del usuario"}
                        },
                        "required": ["user_input"]
                    }
                )
                print(f"[GATHER_AI] Iniciado para Call ID: {call_id}")

        elif event_type == "call.gather.ended":
            asistente_activo[call_id] = False
            transcripcion = payload.get("transcription")
            if transcripcion:
                print(f"[TRANSCRIPCIÓN] {transcripcion}")
                respuesta = generar_respuesta(transcripcion)
                hablar(call_id, respuesta)
                restar_minuto(phone)
                print(f"[MINUTOS RESTADOS] Nuevo total para {phone}: {obtener_minutos(phone)}")
            else:
                print(f"[TRANSCRIPCIÓN VACÍA] Repetir para {phone}")
                hablar(call_id, "No te escuché bien. Por favor, repite.")

        elif event_type == "call.hangup":
            asistente_activo.pop(call_id, None)
            print(f"[HANGUP] Llamada finalizada: {call_id}")

    except Exception as e:
        print(f"[ERROR Webhook] {e}")

    return Response(status_code=200)


def hablar(call_id, texto):
    try:
        # 1️⃣ Generar audio ElevenLabs
        audio = generate(
            text=texto,
            voice="alloy",
            model="eleven_multilingual_v1"
        )

        # 2️⃣ Guardar MP3 en static
        timestamp = int(time.time())
        filename = f"audio_{timestamp}.mp3"
        filepath = os.path.join("static", filename)
        with open(filepath, "wb") as f:
            f.write(audio)
        print(f"[AUDIO GENERADO] {filename}")

        # 3️⃣ Limpiar archivos antiguos
        limpiar_archivos_mp3()

        # 4️⃣ URL público
        audio_url = f"{MI_URL_RENDER}/static/{filename}"

        # 5️⃣ Reproducir en la llamada
        client.calls.actions.audio_playback_start(
            call_control_id=call_id,
            audio_url=audio_url
        )
        print(f"[PLAYBACK START] Call ID: {call_id} | URL: {audio_url}")

    except Exception as e:
        print(f"[ERROR Hablar] {e}")


def limpiar_archivos_mp3():
    files = sorted(glob.glob("static/audio_*.mp3"), key=os.path.getmtime)
    if len(files) > MAX_MP3_FILES:
        for f in files[:-MAX_MP3_FILES]:
            try:
                os.remove(f)
                print(f"[BORRADO] {f}")
            except:
                pass
