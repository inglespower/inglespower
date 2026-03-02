from openai import OpenAI
import elevenlabs # Cambiamos la forma de importar
from elevenlabs.client import ElevenLabs
from config import Config

# Clientes inicializados con nombres distintos
client_openai = OpenAI(api_key=Config.OPENAI_API_KEY)
client_el = ElevenLabs(api_key=Config.ELEVENLABS_API_KEY) # Aquí está el cambio clave

def generar_respuesta(texto_usuario):
    try:
        response = client_openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Eres un tutor de inglés amable. Responde en máximo 2 frases y corrige errores sutilmente."},
                {"role": "user", "content": texto_usuario}
            ]
        )
        return response.choices.message.content
    except Exception as e:
        print(f"Error OpenAI: {e}")
        return "I'm sorry, I'm having trouble thinking."

def texto_a_voz(texto, filepath):
    try:
        # Usamos client_el para llamar a generate
        audio_generator = client_el.generate(
            text=texto,
            voice=Config.ELEVENLABS_VOICE_ID, 
            model="eleven_multilingual_v2"
        )
        
        with open(filepath, "wb") as f:
            for chunk in audio_generator:
                if chunk:
                    f.write(chunk)
        return filepath
    except Exception as e:
        # Este mensaje saldrá en tus logs de Render si hay otro error (como falta de saldo)
        print(f"Error real detectado en ElevenLabs: {e}")
        return None
