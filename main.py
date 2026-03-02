import os
import requests
import telnyx
from fastapi import FastAPI, Request, Response
from openai import OpenAI
from supabase_client import get_minutes, subtract_minute
from ai import generate_reply, get_voice_audio_url

app = FastAPI()

# =========================
# CONFIGURACIÓN
# =========================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELNYX_API_KEY = os.getenv("TELNYX_API_KEY")
TELNYX_NUMBER = os.getenv("TELNYX_NUMBER")
TELNYX_PUBLIC_KEY = os.getenv("TELNYX_PUBLIC_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)
telnyx.api_key = TELNYX_API_KEY

# =========================
# Ruta de prueba
# =========================
@app.get("/")
def home():
    return {"status": "English Power AI running"}

# =========================
# Función para transcribir audio (Whisper)
# =========================
def transcribe_audio(url):
    try:
        audio_data = requests.get(url).content
        temp_file = "/tmp/user_audio.mp3"
        with open(temp_file, "wb") as f:
            f.write(audio_data)

        with open(temp_file, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        return transcript.text
    except Exception as e:
        print("Error transcribing audio:", e)
        return None

# =========================
# WEBHOOK TELNYX
# =========================
@app.post("/webhook")
async def webhook(request: Request):
    try:
        body = await request.json()
    except Exception:
        # Si el webhook viene vacío o malformado, imprimir y responder 200
        body_bytes = await request.body()
        print("Webhook vacío o malformado:", body_bytes)
        return Response(status_code=200)

    event_type = body.get("data", {}).get("event_type")
    payload = body.get("data", {}).get("payload", {})
    call_control_id = payload.get("call_control_id")

    phone = payload.get("from")
    if isinstance(phone, dict):
        phone = phone.get("phone_number")

    print("EVENT:", event_type, "CALL ID:", call_control_id)

    # =========================
    # 1️⃣ Contestar llamada
    # =========================
    if event_type == "call.initiated" and call_control_id:
        telnyx.Call.answer(call_control_id=call_control_id)

    # =========================
    # 2️⃣ Saludo inicial
    # =========================
    elif event_type == "call.answered" and call_control_id:
        minutes = get_minutes(phone)

        if minutes <= 0:
            telnyx.Call.speak(
                call_control_id=call_control_id,
                payload="You have no minutes remaining. Please recharge. Goodbye.",
                voice="female",
                language="en-US"
            )
        else:
            telnyx.Call.speak(
                call_control_id=call_control_id,
                payload="Hello! I am your English Power coach. Tell me something in English.",
                voice="female",
                language="en-US"
            )

    # =========================
    # 3️⃣ Después de hablar → grabar
    # =========================
    elif event_type in ["call.speak.ended", "call.playback.ended"] and call_control_id:
        telnyx.Call.record_start(
            call_control_id=call_control_id,
            format="mp3",
            channels="single",
            play_beep=True,
            max_length=30
        )

    # =========================
    # 4️⃣ Procesar grabación
    # =========================
    elif event_type == "call.recording.saved" and call_control_id:
        recording_url = payload.get("recording_urls", {}).get("mp3")
        if not recording_url:
            return Response(status_code=200)

        user_text = transcribe_audio(recording_url)
        print("USER:", user_text)

        if not user_text:
            telnyx.Call.speak(
                call_control_id=call_control_id,
                payload="I did not hear you. Please try again.",
                voice="female",
                language="en-US"
            )
            return Response(status_code=200)

        subtract_minute(phone)

        reply_text = generate_reply(user_text)
        print("AI:", reply_text)

        audio_url = get_voice_audio_url(reply_text)

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

    return Response(status_code=200)

# =========================
# RENDER
# =========================
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
