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

# Configuración de carpetas para audios temporales de ElevenLabs
if not os.path.exists("static"):
    os.makedirs("static")

# Montamos la carpeta static para que Telnyx pueda descargar los audios
app.mount("/static", StaticFiles(directory="static"), name="static")

# Inicialización de Telnyx v4
client = Telnyx(api_key=Config.TELNYX_API_KEY)
MI_URL_RENDER = "https://inglespower.onrender.com"

@app.get("/")
async def health():
    return {"status": "online", "service": "InglesPower AI Tutor"}

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        event = data.get("data", {})
        payload = event.get("payload", {})
        call_id = payload.get("call_control_id")
        phone = payload.get("from")
        event_type = event.get("event_type")

        # 1. LLAMADA ENTRANTE: Validar minutos
        if event_type == "call.initiated":
            minutos = obtener_minutos(phone)
            if minutos > 0:
                print(f"Llamada de {phone} aceptada. Saldo: {minutos} min.")
                client.calls.actions.answer(call_id)
            else:
                print(f"Llamada rechazada por falta de saldo: {phone}")
                client.calls.actions.hangup(call_id)

        # 2. LLAMADA CONTESTADA: Saludo inicial con ElevenLabs
        elif event_type == "call.answered":
            time.sleep(1.5) # Delay para estabilizar el audio
            hablar(call_id, "Welcome to your English practice. I am Rachel, your AI tutor. How can I help you today?")

        # 3. ACTIVAR ESCUCHA: Cuando el bot termina de hablar
        elif event_type in ["call.speak.ended", "call.playback.ended"]:
            # CORRECCIÓN ERROR 422: Estructura obligatoria de 'properties'
            client.calls.actions.gather_using_ai(
                call_id, 
                parameters={
                    "language": "en-US",
                    "type": "object",
                    "properties": {
                        "user_response": {
                            "type": "string",
                            "description": "Transcripción del usuario"
                        }
                    },
                    "required": ["user_response"]
                }
            )

        # 4. PROCESAR RESPUESTA: Lo que el usuario dijo
        elif event_type == "call.gather.ended":
            transcripcion = payload.get("transcription")
            if transcripcion:
                print(f"Usuario dijo: {transcripcion}")
                respuesta_texto = generar_respuesta(transcripcion)
                hablar(call_id, respuesta_texto)
                restar_minuto(phone)
            else:
                hablar(call_id, "I'm sorry, I didn't hear you. Could you repeat that?")

    except Exception as e:
        print(f"Error crítico en Webhook: {e}")

    return Response(status_code=200)

def hablar(call_id, texto):
    """Genera audio realista con ElevenLabs y lo reproduce en la llamada."""
    try:
        filename = f"audio_{int(time.time())}.mp3"
        filepath = os.path.join("static", filename)
        
        # Llamada a ai.py para generar el archivo físico
        archivo_generado = texto_a_voz(texto, filepath)
        
        if archivo_generado:
            audio_url = f"{MI_URL_RENDER}/static/{filename}"
            print(f"Reproduciendo audio ElevenLabs: {audio_url}")
            client.calls.actions.playback_start(call_id, audio_url=audio_url)
        else:
            # Fallback a voz robótica si falla ElevenLabs (sin saldo/error API)
            print("Fallo ElevenLabs, usando voz de respaldo (Telnyx)...")
            client.calls.actions.speak(call_id, payload=texto, voice="female", language="en-US")
    except Exception as e:
        print(f"Error al ejecutar comando hablar: {e}")
