import os
import requests
import telnyx
from fastapi import FastAPI, Request, Response
from openai import OpenAI

# Importaciones de tus archivos locales
from supabase_client import get_minutes, subtract_minute
from ai import generate_reply, get_nathaniel_voice_url

app = FastAPI()

# Configuración de Clientes
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
telnyx.api_key = os.environ.get("TELNYX_API_KEY")

# ==========================================
# FUNCION AUXILIAR PARA VOZ A TEXTO (Whisper)
# ==========================================
def transcribe_audio(url):
    try:
        # Descargar el audio que grabó Telnyx
        audio_data = requests.get(url).content
        temp_filename = "user_voice.mp3"
        with open(temp_filename, "wb") as f:
            f.write(audio_data)
        
        # Enviar a OpenAI Whisper
        with open(temp_filename, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file
            )
        return transcript.text
    except Exception as e:
        print(f"Error en transcripción: {e}")
        return None

# ==========================================
# WEBHOOK PRINCIPAL (TELNYX)
# ==========================================
@app.post("/webhook")
async def telnyx_webhook(request: Request):
    data = await request.json()
    event = data.get("data", {})
    event_type = event.get("event_type")
    payload = event.get("payload", {})
    call_control_id = payload.get("call_control_id")
    
    # Extraer el número de teléfono del usuario
    phone = payload.get("from")
    if isinstance(phone, dict): # A veces Telnyx lo envía como objeto
        phone = phone.get("phone_number")

    # 1. INICIO DE LLAMADA
    if event_type == "call.initiated":
        telnyx.Call.answer(call_control_id=call_control_id)

    # 2. LLAMADA CONTESTADA: VERIFICAR MINUTOS Y SALUDAR
    elif event_type == "call.answered":
        minutes = get_minutes(phone)
        if minutes <= 0:
            telnyx.Call.speak(
                call_control_id=call_control_id,
                payload="You have no minutes. Please recharge your account. Goodbye.",
                voice="female", language="en-US"
            )
        else:
            # Saludo inicial
            telnyx.Call.speak(
                call_control_id=call_control_id,
                payload="Hello! I am your English Power coach. How can I help you practice today?",
                voice="female", language="en-US"
            )

    # 3. CUANDO LA IA TERMINA DE HABLAR -> ESCUCHAR AL USUARIO
    elif event_type == "call.speak.ended" or event_type == "call.playback.ended":
        # Empezamos a grabar lo que el usuario dice
        telnyx.Call.record_start(
            call_control_id=call_control_id,
            format="mp3",
            channels="single",
            play_beep=True,
            limit_seconds=15 # Máximo 15 segundos de habla
        )

    # 4. PROCESAR LA GRABACIÓN (EL MOMENTO CLAVE)
    elif event_type == "call.recording.saved":
        recording_url = payload.get('recording_urls', {}).get('mp3')
        
        # A. Transcribir Audio -> Texto
        user_text = transcribe_audio(recording_url)
        print(f"Usuario dijo: {user_text}")

        if user_text:
            # B. Restar minuto (Lógica de tu negocio)
            subtract_minute(phone)

            # C. Generar Respuesta GPT
            reply_text = generate_reply(user_text)
            
            # D. Generar Voz ElevenLabs (URL de Supabase)
            audio_url = get_nathaniel_voice_url(reply_text)

            # E. Responder en la llamada
            if audio_url:
                telnyx.Call.playback_start(call_control_id=call_control_id, audio_url=audio_url)
            else:
                # Si falla ElevenLabs, usar voz robótica de respaldo
                telnyx.Call.speak(call_control_id=call_control_id, payload=reply_text, voice="female", language="en-US")
        else:
            # Si no se entendió nada, pedir repetir
            telnyx.Call.speak(call_control_id=call_control_id, payload="I'm sorry, I didn't catch that. Please try again.", voice="female", language="en-US")

    return Response(status_code=200)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
