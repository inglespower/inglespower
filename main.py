import os
import uuid
import requests
from fastapi import FastAPI, Request, Response
from openai import OpenAI
from supabase_client import get_minutes, subtract_minute
from ai import generate_reply, get_nathaniel_voice_url
import telnyx

app = FastAPI()

# =========================
# CONFIGURACIÓN
# =========================
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
telnyx.api_key = os.environ.get("TELNYX_API_KEY")
TELNYX_NUMBER = os.environ.get("TELNYX_NUMBER")
TELNYX_PUBLIC_KEY = os.environ.get("TELNYX_PUBLIC_KEY")

# =========================
# FUNCIONES AUXILIARES
# =========================
def transcribe_audio(url: str):
    """Descarga audio y lo transcribe con Whisper"""
    try:
        audio_data = requests.get(url).content
        temp_file = "/tmp/user_voice.mp3"
        with open(temp_file, "wb") as f:
            f.write(audio_data)
        with open(temp_file, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        return transcript.text
    except Exception as e:
        print(f"Error en transcripción: {e}")
        return None

# =========================
# WEBHOOK TELNYX
# =========================
@app.post("/webhook")
async def webhook(request: Request):
    try:
        body = await request.json()
    except:
        form_data = await request.form()
        body = {"data": dict(form_data)}
        print("Webhook recibido en formato form:", body)

    event = body.get("data", {})
    event_type = event.get("event_type")
    payload = event.get("payload", {})
    call_control_id = payload.get("call_control_id")

    phone = payload.get("from")
    if isinstance(phone, dict):
        phone = phone.get("phone_number")

    # 1️⃣ Llamada iniciada
    if event_type == "call.initiated":
        telnyx.Call.answer(call_control_id=call_control_id)

    # 2️⃣ Llamada contestada
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

    # 3️⃣ Después de hablar el saludo, grabar al usuario
    elif event_type in ["call.speak.ended", "call.playback.ended"]:
        telnyx.Call.record_start(
            call_control_id=call_control_id,
            format="mp3",
            channels="single",
            play_beep=True,
            limit_seconds=30
        )

    # 4️⃣ Procesar grabación del usuario
    elif event_type == "call.recording.saved":
        recording_url = payload.get('recording_urls', {}).get('mp3')
        user_text = transcribe_audio(recording_url)

        if user_text:
            subtract_minute(phone)
            reply_text = generate_reply(user_text)
            audio_url = get_nathaniel_voice_url(reply_text)

            if audio_url:
                telnyx.Call.playback_start(
                    call_control_id=call_control_id,
                    audio_url=audio_url
                )
            else:
                telnyx.Call.speak(
                    call_control_id=call_control_id,
                    payload=reply_text,
                    voice="female",
                    language="en-US"
                )
        else:
            telnyx.Call.speak(
                call_control_id=call_control_id,
                payload="I didn't catch that. Try again.",
                voice="female",
                language="en-US"
            )

    return Response(status_code=200)

# =========================
# EJECUTAR LOCAL O RENDER
# =========================
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
