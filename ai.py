from openai import OpenAI
from elevenlabs.client import ElevenLabs
from config import Config

client_openai = OpenAI(api_key=Config.OPENAI_API_KEY)
# Inicialización correcta del cliente v1.x
client_el = ElevenLabs(api_key=Config.ELEVENLABS_API_KEY)

def generar_respuesta(texto_usuario):
    try:
        response = client_openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system", 
                    "content": "Eres un tutor de inglés. RESPONDE SIEMPRE EN ESPAÑOL. Sé breve y amable. Máximo 2 frases."
                },
                {"role": "user", "content": texto_usuario}
            ]
        )
        return response.choices.message.content
    except Exception as e:
        print(f"Error OpenAI: {e}")
        return "Lo siento, tuve un problema técnico."

def texto_a_voz(texto, filepath):
    """Genera audio usando la ruta de comando estándar de la v1.x."""
    try:
        # SINTAXIS PARA SDK v1.x: Usamos text_to_speech.convert para evitar errores de atributo
        audio_generator = client_el.text_to_speech.convert(
            voice_id=Config.ELEVENLABS_VOICE_ID,
            text=texto,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128"
        )
        
        with open(filepath, "wb") as f:
            for chunk in audio_generator:
                if chunk:
                    f.write(chunk)
        return filepath
    except Exception as e:
        # Si escuchas voz de robot, este mensaje en Render te dirá por qué falló
        print(f"FALLO CRÍTICO ELEVENLABS: {e}")
        return None
