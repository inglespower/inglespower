import os
import uuid
import json
import requests
from fastapi import FastAPI, Request
from supabase import create_client
from openai import OpenAI

app = FastAPI()

# ----- Configuración OpenAI -----
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# ----- Configuración Supabase -----
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ----- Configuración ElevenLabs -----
ELEVEN_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
ELEVEN_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID")

# ----- Configuración Telnyx -----
TELNYX_API_KEY = os.environ.get("TELNYX_API_KEY")
TELNYX_PHONE_NUMBER = os.environ.get("TELNYX_PHONE_NUMBER")

# ---------------- Funciones ----------------

def generate_reply(text: str) -> str:
    """
    Genera la respuesta de la AI usando ChatGPT
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are English Power, a friendly English coach. Correct mistakes and encourage the student. Be brief."
            },
            {"role": "user", "content": text}
        ],
        max_tokens=120
    )
    return response.choices[0].message.content

def get_voice_audio_url(text: str) -> str:
    """
    Convierte texto a voz con ElevenLabs y sube a Supabase
    """
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

async def transcribe_audio(file_url: str) -> str:
    """
    Transcribe audio usando Whisper de OpenAI
    """
    audio_resp = requests.get(file_url)
    audio_bytes = audio_resp.content

    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_bytes
    )
    return transcript.text

# ---------------- Rutas ----------------

@app.post("/webhook")
async def webhook(request: Request):
    """
    Webhook que recibe eventos de Telnyx (llamadas entrantes)
    """
    try:
        body_bytes = await request.body()
        body_text = body_bytes.decode("utf-8")
        # Telnyx envía datos como x-www-form-urlencoded, no JSON
        data = dict(item.split("=") for item in body_text.split("&"))

        audio_url = data.get("RecordingUrl")  # Suponiendo que Telnyx manda RecordingUrl
        if not audio_url:
            return {"error": "No audio found in webhook"}

        user_text = await transcribe_audio(audio_url)
        ai_text = generate_reply(user_text)
        ai_audio_url = get_voice_audio_url(ai_text)

        return {"reply_text": ai_text, "reply_audio": ai_audio_url}

    except Exception as e:
        print("Error en webhook:", e)
        return {"error": str(e)}

@app.get("/")
async def root():
    return {"status": "English Power AI running ✅"}
