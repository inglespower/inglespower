from openai import OpenAI
from config import Config

client = OpenAI(api_key=Config.OPENAI_API_KEY)

# -------------------------
# VOZ → TEXTO (Whisper)
# -------------------------
async def speech_to_text(audio_bytes):
    with open("/tmp/audio.wav", "wb") as f:
        f.write(audio_bytes)

    with open("/tmp/audio.wav", "rb") as f:
        result = client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=f
        )

    return result.text


# -------------------------
# CEREBRO (GPT)
# -------------------------
async def ask_ai(text):
    response = client.responses.create(
        model="gpt-4o-mini",
        input=f"""
Eres Thorthugo, un tutor de inglés.

Reglas:
- Responde en español
- Enseña inglés naturalmente
- Máximo 2 frases
- Siempre incluye un ejemplo en inglés

Usuario: {text}
"""
    )

    return response.output_text


# -------------------------
# TEXTO → VOZ (TTS OpenAI)
# -------------------------
async def text_to_speech(text):
    audio = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="alloy",
        input=text
    )

    return audio.read()
