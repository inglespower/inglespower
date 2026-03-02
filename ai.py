from openai import OpenAI
from elevenlabs.client import ElevenLabs
from config import Config
import os

# Inicialización de clientes
client_openai = OpenAI(api_key=Config.OPENAI_API_KEY)
client_eleven = ElevenLabs(api_key=Config.ELEVENLABS_API_KEY)

def generar_respuesta(texto_usuario):
    """Genera el texto de respuesta usando GPT-4o."""
    try:
        response = client_openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Eres un tutor de inglés nativo. Sé breve (máximo 2 frases) y amable."},
                {"role": "user", "content": texto_usuario}
            ]
        )
        return response.choices.message.content
    except Exception as e:
        print(f"Error en OpenAI: {e}")
        return "I'm sorry, can you repeat that?"

def texto_a_voz(texto, filename="respuesta.mp3"):
    """Convierte texto en audio usando ElevenLabs y lo guarda localmente."""
    try:
        audio = client_eleven.generate(
            text=texto,
            voice="Rachel", # Puedes cambiar el nombre de la voz aquí
            model="eleven_multilingual_v2"
        )
        
        # Guardar el archivo temporalmente en el servidor
        with open(filename, "wb") as f:
            for chunk in audio:
                f.write(chunk)
        return filename
    except Exception as e:
        print(f"Error en ElevenLabs: {e}")
        return None
