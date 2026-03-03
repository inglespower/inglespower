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

# Asegurar que la carpeta static existe para los audios
if not os.path.exists("static"):
    os.makedirs("static")

# Montar static para que Telnyx pueda descargar los archivos .mp3
app.mount("/static", StaticFiles(directory="static"), name="static")

client = Telnyx(api_key=Config.TELNYX_API_KEY)
MI_URL_RENDER = "https://inglespower.onrender.com"

# Evitar que el asistente de IA se active dos veces seguidas
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

        # 1. Entrada de llamada
        if event_type == "call.initiated":
            minutos = obtener_minutos(phone)
            if minutos > 0:
                print(f"Llamada aceptada: {phone}. Saldo: {minutos}")
                client.calls.actions.answer(call_id)
                asistente_activo[call_id] = False
            else:
                client.calls.actions.hangup(call_id)

        # 2. Saludo inicial en Español
        elif event_type == "call.answered":
            time.sleep(1.5)
            hablar(call_id, "Hola, soy tu tutor personal de inglés. ¿Qué te gustaría aprender hoy?")

        # 3. Activar "oído" en Español (es-MX)
        elif event_type in ["call.speak.ended", "call.playback.ended"]:
            if not asistente_activo.get(call_id, False):
                asistente_activo[call_id] = True
                client.calls.actions.gather_using_ai(
                    call_id, 
                    parameters={
                        "language": "es-MX", # Crucial para entender "gato"
                        "type": "object",
                        "properties": {
                            "user_input": {"type": "string", "description": "Response"}
                        },
                        "required": ["user_input"]
                    }
                )

        # 4. Procesar lo que el usuario dijo
        elif event_type == "call.gather.ended":
            asistente_activo[call_id] = False
            transcripcion = payload.get("transcription")
            if transcripcion:
                print(f"Usuario: {transcripcion}")
                respuesta_texto = generar_respuesta(transcripcion)
                hablar(call_id, respuesta_texto)
                restar_minuto(phone)
            else:
                hablar(call_id, "No te escuché bien. ¿Podrías repetirlo?")

    except Exception as e:
        print(f"Error en Webhook: {e}")

    return Response(status_code=200)

def hablar(call_id, texto):
    """Reproduce el audio realista de ElevenLabs."""
    try:
        filename = f"audio_{int(time.time())}.mp3"
        filepath = os.path.join("static", filename)
        
        # Llamar a ElevenLabs
        archivo_generado = texto_a_voz(texto, filepath)
        
        if archivo_generado:
            # Si se generó el audio, lo reproducimos (Voz real)
            audio_url = f"{MI_URL_RENDER}/static/{filename}"
            print(f"Reproduciendo voz ElevenLabs: {audio_url}")
            client.calls.actions.playback_start(call_id, audio_url=audio_url)
        else:
            # Si falla, usamos la voz de robot (Voz de respaldo)
            print("Fallback: Usando voz de robot de Telnyx")
            client.calls.actions.speak(call_id, payload=texto, voice="female", language="es-MX")
    except Exception as e:
        print(f"Error al intentar hablar: {e}")
