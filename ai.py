import os
import requests
import uuid
from openai import OpenAI
from supabase import create_client

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

ELEVEN_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
ELEVEN_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID")


def generate_reply(text):
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


def get_voice_audio_url(text):

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVEN_VOICE_ID}"

    headers = {
        "xi-api-key": ELEVEN_API_KEY,
        "Content-Type": "application/json"
    }

    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2"
    }

    response = requests.post(url, json=data, headers=headers)

    if response.status_code != 200:
        print("ElevenLabs error:", response.text)
        return None

    file_name = f"reply_{uuid.uuid4()}.mp3"

    supabase.storage.from_("audios").upload(
        path=file_name,
        file=response.content,
        file_options={"content-type": "audio/mpeg"}
    )

    public_url = supabase.storage.from_("audios").get_public_url(file_name)

    return public_url
