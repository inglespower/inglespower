import os
import uuid
import requests
from fastapi import FastAPI, Form, Request, Response
from openai import OpenAI
from supabase import create_client
import telnyx

# =========================
# CONFIGURACIÓN
# =========================
app = FastAPI()

# OpenAI
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# ElevenLabs
ELEVEN_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
ELEVEN_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID")

# Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Telnyx
TELNYX_API_KEY = os.environ.get("TELNYX_API_KEY")
TELNYX_PHONE_NUMBER = os.environ.get("TELNYX_PHONE_NUMBER")
TELNYX_PUBLIC_KEY = os.environ.get("TELNYX_PUBLIC_KEY")  # opcional según tu flujo
telnyx.api_key = TELNYX_API_KEY

# =========================
# FUNCIONES AUXILIARES
# =========================
def transcribe_audio(audio_url: str):
    """Descarga el audio y lo transcribe con Whisper"""
    audio_data = requests.get(audio_url).content
    temp_file = f"/tmp/recording_{uuid.uuid4()}.mp3"
    with open(temp_file, "wb") as f:
        f.write(audio_data)
    with open(temp_file, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
    return transcript.text

def generate_reply(text: str):
    """Genera respuesta GPT breve y motivadora"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are English Power, a friendly English coach. Correct mistakes and encourage the student. Be brief."},
            {"role": "user", "content": text}
        ],
        max_tokens=120
    )
    return response.choices[0].message.content

def get_voice_audio_url(text: str):
    """Genera audio con ElevenLabs y lo sube a Supabase"""
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVEN_VOICE_ID}"
    headers = {"xi-api-key": ELEVEN_API_KEY, "Content-Type": "application/json"}
    data = {"text": text, "model_id": "eleven_multilingual_v2"}
    
    resp = requests.post(url, json=data, headers=headers)
    if resp.status_code != 200:
        print("ElevenLabs error:", resp.text)
        return None

    file_name = f"reply_{uuid.uuid4()}.mp3"
    supabase.storage.from_("audios").upload(
        path=file_name,
        file=resp.content,
        file_options={"content-type": "audio/mpeg"}
    )
    public_url = supabase.storage.from_("audios").get_public_url(file_name)
    return public_url

# =========================
# WEBHOOK TELNYX
# =========================
@app.post("/webhook")
async def telnyx_webhook(request: Request):
    """
    Recibe webhooks de Telnyx (URL-encoded)
    """
    form = await request.form()  # <- IMPORTANTE para evitar JSONDecodeError
    event_type = form.get("EventType") or form.get("event_type")
    call_control_id = form.get("CallControlId") or form.get("call_control_id")
    
    if not call_control_id:
        return Response(content="Missing call_control_id", status_code=400)

    # =====================
    # 1. Contestar la llamada
    # =====================
    if event_type == "call.initiated":
        telnyx.Call.answer(call_control_id=call_control_id)

    # =====================
    # 2. Hablar con el usuario
    # =====================
    elif event_type == "call.answered":
        telnyx.Call.speak(
            call_control_id=call_control_id,
            payload="Hi! I'm your English coach. How can I help you today?",
            voice="female",
            language="en-US"
        )

    # =====================
    # 3. Comenzar grabación
    # =====================
    elif event_type in ["call.speak.ended", "call.playback.ended"]:
        telnyx.Call.record_start(
            call_control_id=call_control_id,
            format="mp3",
            channels="single",
            play_beep=True,
            limit_seconds=30
        )

    # =====================
    # 4. Procesar grabación y responder
    # =====================
    elif event_type == "call.recording.saved":
        recording_url = form.get("RecordingUrls") or form.get("recording_urls")
        if recording_url:
            # Puede venir como dict en string, lo convertimos
            if isinstance(recording_url, str):
                import json
                try:
                    recording_url = json.loads(recording_url)
                except:
                    pass
            mp3_url = recording_url.get("mp3") if isinstance(recording_url, dict) else recording_url
            if mp3_url:
                user_text = transcribe_audio(mp3_url)
                print("Usuario dijo:", user_text)
                reply_text = generate_reply(user_text)
                print("AI responde:", reply_text)
                audio_url = get_voice_audio_url(reply_text)
                if audio_url:
                    telnyx.Call.playback_start(call_control_id=call_control_id, audio_url=audio_url)
                else:
                    telnyx.Call.speak(call_control_id=call_control_id, payload=reply_text, voice="female", language="en-US")
            else:
                telnyx.Call.speak(call_control_id=call_control_id, payload="I didn't catch that. Try again.", voice="female", language="en-US")
        else:
            telnyx.Call.speak(call_control_id=call_control_id, payload="No recording URL found.", voice="female", language="en-US")

    return Response(status_code=200)

# =========================
# RENDER PUERTO
# =========================
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
