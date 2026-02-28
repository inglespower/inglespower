import os
import requests
import telnyx
from fastapi import FastAPI, Request, Response
from openai import OpenAI
from supabase_client import get_minutes, subtract_minute
from ai import generate_reply, get_nathaniel_voice_url

app = FastAPI()

# Configuración de Clientes
# Render leerá estas variables de tu sección 'Environment'
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
telnyx.api_key = os.environ.get("TELNYX_API_KEY")

# ==========================================
# FUNCION AUXILIAR PARA VOZ A TEXTO (Whisper)
# ==========================================
def transcribe_audio(url):
    try:
        audio_data = requests.get(url).content
        temp_filename = "/tmp/user_voice.mp3" # Usamos /tmp para Render
        with open(temp_filename, "wb") as f:
            f.write(audio_data)
        
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
    
    phone = payload.get("from")
    if isinstance(phone, dict):
        phone = phone.get("phone_number")

    # 1. INICIO DE LLAMADA
    if event_type == "call.initiated":
        telnyx.Call.answer(call_control_id=call_control_id)

    # 2. LLAMADA CONTESTADA
    elif event_type == "call.answered":
        minutes = get_minutes(phone)
        if minutes <= 0:
            telnyx.Call.speak(
                call_control_id=call_control_id,
                payload="You have no minutes. Please recharge. Goodbye.",
                voice="female", language="en-US"
            )
        else:
            telnyx.Call.speak(
                call_control_id=call_control_id,
                payload="Hello! I am your English Power coach. How can I help you practice today?",
                voice="female", language="en-US"
            )

    # 3. ESCUCHAR AL USUARIO
    elif event_type in ["call.speak.ended", "call.playback.ended"]:
        telnyx.Call.record_start(
            call_control_id=call_control_id,
            format="mp3",
            channels="single",
            play_beep=True,
            limit_seconds=15
        )

    # 4. PROCESAR GRABACIÓN
    elif event_type == "call.recording.saved":
        recording_url = payload.get('recording_urls', {}).get('mp3')
        user_text = transcribe_audio(recording_url)

        if user_text:
            subtract_minute(phone)
            reply_text = generate_reply(user_text)
            audio_url = get_nathaniel_voice_url(reply_text)

            if audio_url:
                telnyx.Call.playback_start(call_control_id=call_control_id, audio_url=audio_url)
            else:
                telnyx.Call.speak(call_control_id=call_control_id, payload=reply_text, voice="female", language="en-US")
        else:
            telnyx.Call.speak(call_control_id=call_control_id, payload="I didn't catch that. Try again.", voice="female", language="en-US")

    return Response(status_code=200)

# ==========================================
# CONFIGURACIÓN PARA RENDER (PUERTOS)
# ==========================================
if __name__ == "__main__":
    import uvicorn
    # Render usa la variable PORT. Si no existe, usa 10000.
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
