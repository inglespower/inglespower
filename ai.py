from openai import OpenAI
from elevenlabs.client import ElevenLabs
from config import Config

# Inicialización de clientes
client_openai = OpenAI(api_key=Config.OPENAI_API_KEY)
client_eleven = ElevenLabs(api_key=Config.ELEVENLABS_API_KEY)

def generar_respuesta(texto_usuario):
    """Genera texto breve con GPT-4o."""
    try:
        response = client_openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Eres un tutor de inglés amable. Responde en máximo 2 frases breves y corrige errores sutilmente."},
                {"role": "user", "content": texto_usuario}
            ]
        )
        return response.choices.message.content
    except Exception as e:
        print(f"Error OpenAI: {e}")
        return "I am sorry, I had a problem processing that."

def texto_a_voz(texto, filepath):
    """Convierte texto a audio con ElevenLabs usando la sintaxis de cliente corregida."""
    try:
        # CORRECCIÓN: Se usa client_eleven.generate y se itera sobre el resultado
        audio_generator = client_eleven.generate(
            text=texto,
            voice="Rachel", 
            model="eleven_multilingual_v2"
        )
        
        with open(filepath, "wb") as f:
            for chunk in audio_generator:
                if chunk:
                    f.write(chunk)
        return filepath
    except Exception as e:
        print(f"Error en ElevenLabs: {e}")
        return None
