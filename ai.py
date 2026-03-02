import os
import requests
import uuid
from openai import OpenAI
from supabase import create_client

# =========================
# CONFIGURACIÓN
# =========================
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ELEVEN_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
ELEVEN_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Inicializamos clientes
client = OpenAI(api_key=OPENAI_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# =========================
# GENERACIÓN DE RESPUESTA GPT
# =========================
def generate_reply(user_text: str) -> str:
    """
    Genera una respuesta breve y alentadora de GPT-4 para el estudiante.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are English Power, a friendly English coach. "
                        "Correct mistakes and encourage the student. Be brief."
                    )
                },
                {"role": "user", "content": user_text}
            ],
            max_tokens=120
        )
        return response.choices[0].message.content
    except Exception as e:
        print("Error GPT:", e)
        return "I'm sorry, I cannot respond right now."


# =========================
# GENERACIÓN DE VOZ (ElevenLabs)
# =========================
def get_nathaniel_voice_url(text: str) -> str:
    """
    Convierte un texto en audio usando ElevenLabs y devuelve la URL pública en Supabase.
    """
    try:
        eleven_url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVEN_VOICE_ID}"
        headers = {"xi-api-key": ELEVEN_API_KEY, "Content-Type": "application/json"}
        data = {"text": text, "model_id": "eleven_multilingual_v2"}

        response = requests.post(eleven_url, json=data, headers=headers)
        if response.status_code != 200:
            print("ElevenLabs error:", response.text)
            return None

        # Guardamos y subimos el audio a Supabase
        file_name = f"reply_{uuid.uuid4()}.mp3"
        supabase.storage.from_("audios").upload(
            path=file_name,
            file=response.content,
            file_options={"content-type": "audio/mpeg"}
        )

        # Retornamos la URL pública
        public_url = supabase.storage.from_("audios").get_public_url(file_name)
        return public_url
    except Exception as e:
        print("Error ElevenLabs:", e)
        return None
