from openai import OpenAI
from elevenlabs.client import ElevenLabs
from config import Config

# Inicialización de clientes
client_openai = OpenAI(api_key=Config.OPENAI_API_KEY)
client_el = ElevenLabs(api_key=Config.ELEVENLABS_API_KEY)

def generar_respuesta(texto_usuario):
    """Genera respuesta breve en español con GPT-4o."""
    try:
        response = client_openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system", 
                    "content": (
                        "Eres un tutor de inglés amable. RESPONDE SIEMPRE EN ESPAÑOL. "
                        "Sé muy breve (máximo 2 frases). Enseña inglés usando el español."
                    )
                },
                {"role": "user", "content": texto_usuario}
            ]
        )
        return response.choices.message.content
    except Exception as e:
        print(f"Error OpenAI: {e}")
        return "Lo siento, tuve un problema técnico. ¿Puedes repetir?"

def texto_a_voz(texto, filepath):
    """Genera audio con la sintaxis exacta del SDK moderno (v1.x)."""
    try:
        # SINTAXIS PARA SDK v1.x: Usamos text_to_speech.convert
        audio_generator = client_el.text_to_speech.convert(
            voice_id=Config.ELEVENLABS_VOICE_ID,
            text=texto,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128"
        )
        
        # Guardamos el archivo .mp3
        with open(filepath, "wb") as f:
            for chunk in audio_generator:
                if chunk:
                    f.write(chunk)
        return filepath
    except Exception as e:
        print(f"FALLO CRÍTICO ELEVENLABS: {e}")
        return None
