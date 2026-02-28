import os
import uuid
import requests
from openai import OpenAI

# =========================
# CONFIGURACIÓN SEGURA
# =========================

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ELEVEN_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
ELEVEN_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Crear cliente OpenAI solo si existe la key
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


# =========================
# GENERAR RESPUESTA GPT
# =========================

def generate_reply(user_text):

    if not client:
        return "OpenAI is not configured."

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are InglesPower, a bilingual English coach. Be brief and encouraging."
                },
                {"role": "user", "content": user_text}
            ],
            max_tokens=120
        )

        return response.choices[0].message.content

    except Exception as e:
        print("OpenAI Error:", e)
        return "Keep going. I am listening."


# =========================
# ELEVENLABS → MP3 DIRECTO
# =========================

def get_nathaniel_voice_url(text):

    if not ELEVEN_API_KEY or not ELEVEN_VOICE_ID:
        print("ElevenLabs not configured.")
        return None

    try:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVEN_VOICE_ID}"

        headers = {
            "xi-api-key": ELEVEN_API_KEY,
            "Content-Type": "application/json"
        }

        data = {
            "text": text,
            "model_id": "eleven_multilingual_v2"
        }

        response = requests.post(url, json=data, headers=headers, timeout=30)

        if response.status_code != 200:
            print("ElevenLabs error:", response.text)
            return None

        # ⚠️ Aquí NO usamos Supabase para evitar crash
        # Guardamos archivo local temporal

        file_name = f"/tmp/voice_{uuid.uuid4()}.mp3"

        with open(file_name, "wb") as f:
            f.write(response.content)

        # IMPORTANTE:
        # Necesitas servir estáticos en FastAPI si quieres usar esto.
        # Si no, vuelve a usar Supabase cuando todo esté estable.

        return None  # Temporal hasta que confirmemos estabilidad

    except Exception as e:
        print("ElevenLabs Exception:", e)
        return None
