import os
import uuid
import requests
import openai
from supabase import create_client

# =========================
# CONFIGURACIÓN
# =========================

openai.api_key = os.environ.get("OPENAI_API_KEY")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

ELEVEN_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
ELEVEN_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID")

# =========================
# GENERAR RESPUESTA GPT
# =========================

def generate_reply(user_text):

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are InglesPower, a bilingual English coach. Be brief and encouraging."
                },
                {"role": "user", "content": user_text}
            ],
            max_tokens=120
        )

        return response["choices"][0]["message"]["content"]

    except Exception as e:
        print("OpenAI Error:", e)
        return "Keep going. I am listening."


# =========================
# ELEVENLABS + SUPABASE
# =========================

def get_nathaniel_voice_url(text):

    if not ELEVEN_API_KEY or not ELEVEN_VOICE_ID:
        print("ElevenLabs not configured.")
        return None

    if not supabase:
        print("Supabase not configured.")
        return None

    try:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVEN_VOICE_ID}"

        headers = {
            "xi-api-key": ELEVEN_API_KEY,
            "Content-Type": "application/json"
        }

        data = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }

        response = requests.post(url, json=data, headers=headers, timeout=30)

        if response.status_code != 200:
            print("ElevenLabs Error:", response.text)
            return None

        file_name = f"voice_{uuid.uuid4()}.mp3"

        supabase.storage.from_("audios").upload(
            path=file_name,
            file=response.content,
            file_options={"content-type": "audio/mpeg"}
        )

        public_url = supabase.storage.from_("audios").get_public_url(file_name)

        return public_url

    except Exception as e:
        print("Voice Error:", e)
        return None
