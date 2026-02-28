import os
import uuid
import requests
from openai import OpenAI
from supabase import create_client

# =========================
# CONFIG
# =========================

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
ELEVEN_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "").strip()
ELEVEN_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "").strip()
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip()

client = OpenAI(api_key=OPENAI_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# =========================
# GPT RESPONSE
# =========================

def generate_reply(user_text):

    system_prompt = """
    You are InglesPower, a bilingual English coach.
    Be brief.
    Correct pronunciation.
    Encourage the student.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ],
            max_tokens=120
        )

        return response.choices[0].message.content

    except Exception as e:
        print("Error OpenAI:", e)
        return "Keep going, I am listening."

# =========================
# ELEVENLABS VOICE
# =========================

def get_nathaniel_voice_url(text):

    if not ELEVEN_API_KEY or not ELEVEN_VOICE_ID:
        print("Faltan variables ElevenLabs")
        return None

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

    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)

        if response.status_code == 200:

            file_name = f"voice_{uuid.uuid4()}.mp3"

            supabase.storage.from_("audios").upload(
                path=file_name,
                file=response.content,
                file_options={"content-type": "audio/mpeg"}
            )

            public_url = supabase.storage.from_("audios").get_public_url(file_name)

            return public_url

        else:
            print("Error ElevenLabs:", response.status_code)
            print(response.text)
            return None

    except Exception as e:
        print("Error ElevenLabs:", e)
        return None
