from openai import OpenAI
from elevenlabs.client import ElevenLabs
from config import Config

# Inicialización de clientes
client_openai = OpenAI(api_key=Config.OPENAI_API_KEY)
# El objeto se llama client_eleven para no confundirlo
client_eleven = ElevenLabs(api_key=Config.ELEVENLABS_API_KEY)

def generar_respuesta(texto_usuario):
    """Genera el texto de respuesta con GPT-4o."""
    try:
        response = client_openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Eres un tutor de inglés amable. Responde brevemente (máximo 2 frases) y corrige errores sutilmente."},
                {"role": "user", "content": texto_usuario}
            ]
        )
        return response.choices.message.content
    except Exception as e:
        print(f"Error en OpenAI: {e}")
        return "I am sorry, I am having trouble thinking right now."

def texto_a_voz(texto, filepath):
    """Genera audio con ElevenLabs usando tu VOICE_ID de Render."""
    try:
        # CORRECCIÓN DEFINITIVA: Se usa client_eleven.generate
        audio_generator = client_eleven.generate(
            text=texto,
            voice=Config.ELEVENLABS_VOICE_ID, # Usa tu ID de las variables de entorno
            model="eleven_multilingual_v2"
        )
        
        # Guardar el archivo físico en el servidor
        with open(filepath, "wb") as f:
            for chunk in audio_generator:
                if chunk:
                    f.write(chunk)
        return filepath
    except Exception as e:
        print(f"Error crítico en ElevenLabs: {e}")
        return None
