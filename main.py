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

client = Telnyx(api_key=Config.TELNYX_API_KEY)
MI_URL_RENDER = "https://inglespower.onrender.com"

# Control para evitar errores de comandos duplicados
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

        # 1. LLAMADA INICIADA
        if event_type == "call.initiated":
            minutos = obtener_minutos(phone)
            if minutos > 0:
                print(f"Llamada aceptada: {phone}. Saldo: {minutos}")
                client.calls.actions.answer(call_id)
                asistente_activo[call_id] = False
            else:
                client.calls.actions.hangup(call_id)

        # 2. LLAMADA CONTESTADA: Saludo en Español
        elif event_type == "call.answered":
            time.sleep(1.5)
            hablar(call_id, "Hola, soy tu tutor personal. ¿Qué te gustaría practicar en inglés hoy?")

        # 3. ACTIVAR ESCUCHA: Configurado para entender ESPAÑOL
        elif event_type in ["call.speak.ended", "call.playback.ended"]:
            if not asistente_activo.get(call_id, False):
                asistente_activo[call_id] = True
                client.calls.actions.gather_using_ai(
                    call_id, 
                    parameters={
                        "language": "es-MX", # <--- CLAVE: Entiende español perfectamente
                        "type": "object",
                        "properties": {
                            "user_input": {"type": "string", "description": "Respuesta del alumno"}
                        },
                        "required": ["user_input"]
                    }
                )

        # 4. PROCESAR RESPUESTA
        elif event_type == "call.gather.ended":
            asistente_activo[call_id] = False
            transcripcion = payload.get("transcription")
            if transcripcion:
                print(f"Alumno dijo: {transcripcion}")
                respuesta_texto = generar_respuesta(transcripcion)
                hablar(call_id, respuesta_texto)
                restar_minuto(phone)
            else:
                hablar(call_id, "No te escuché bien. ¿Podrías repetirlo en español?")

    except Exception as e:
        print(f"Error en Webhook: {e}")

    return Response(status_code=200)

def hablar(call_id, texto):
    """Reproduce audio de ElevenLabs en la llamada."""
    try:
        filename = f"audio_{int(time.time())}.mp3"
        filepath = os.path.join("static", filename)
        
        archivo_generado = texto_a_voz(texto, filepath)
        
        if archivo_generado:
            audio_url = f"{MI_URL_RENDER}/static/{filename}"
            client.calls.actions.playback_start(call_id, audio_url=audio_url)
        else:
            # Fallback a voz de Telnyx en español si ElevenLabs falla
            client.calls.actions.speak(call_id, payload=texto, voice="female", language="es-MX")
    except Exception as e:
        print(f"Error al hablar: {e}")
