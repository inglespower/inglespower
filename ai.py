from openai import OpenAI
from elevenlabs.client import ElevenLabs
from config import Config

# Inicialización de clientes
client_openai = OpenAI(api_key=Config.OPENAI_API_KEY)
client_el = ElevenLabs(api_key=Config.ELEVENLABS_API_KEY)

def generar_respuesta(texto_usuario):
    """Genera respuesta de un tutor de inglés que habla español."""
    try:
        response = client_openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system", 
                    "content": (
                        "Eres un tutor de inglés nativo experto en enseñar a hispanohablantes. "
                        "DEBES RESPONDER SIEMPRE EN ESPAÑOL de forma amable y muy breve (máximo 2 frases). "
                        "Si el usuario te pregunta algo en español, respóndele en español y enséñale la traducción al inglés. "
                        "Si el usuario intenta hablar inglés, corrígelo sutilmente en español."
                    )
                },
                {"role": "user", "content": texto_usuario}
            ]
        )
        return response.choices.message.content
    except Exception as e:
        print(f"Error OpenAI: {e}")
        return "Lo siento, tuve un problema al procesar tu respuesta. ¿Puedes repetir?"

def texto_a_voz(texto, filepath):
    """Convierte texto a audio realista usando tu VOICE_ID de ElevenLabs."""
    try:
        # Usamos el modelo multilingual_v2 para que el acento español sea natural
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
        print(f"Error crítico en ElevenLabs: {e}")
        return None
