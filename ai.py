from openai import OpenAI
from elevenlabs.client import ElevenLabs
from config import Config

# Inicialización de clientes
client_openai = OpenAI(api_key=Config.OPENAI_API_KEY)
client_el = ElevenLabs(api_key=Config.ELEVENLABS_API_KEY)

def generar_respuesta(texto_usuario):
    """Genera la respuesta del tutor asegurando que sea en ESPAÑOL."""
    try:
        response = client_openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system", 
                    "content": (
                        "Eres un tutor de inglés nativo experto en enseñar a hispanohablantes. "
                        "REGLA DE ORO: RESPONDE SIEMPRE EN ESPAÑOL. "
                        "Sé amable y muy breve (máximo 2 frases). "
                        "Si el usuario pregunta algo en español, explícale la respuesta en español y dale el ejemplo en inglés. "
                        "Si habla en inglés, corrígelo sutilmente usando el español."
                    )
                },
                {"role": "user", "content": texto_usuario}
            ]
        )
        return response.choices.message.content
    except Exception as e:
        print(f"Error en OpenAI: {e}")
        return "Lo siento, tuve un problema al procesar tu respuesta. ¿Puedes repetir?"

def texto_a_voz(texto, filepath):
    """Convierte texto a audio realista usando tu Voice ID configurado."""
    try:
        # Generamos el audio usando el modelo multilingüe para que el español suene natural
        audio_generator = client_el.generate(
            text=texto,
            voice=Config.ELEVENLABS_VOICE_ID, 
            model="eleven_multilingual_v2"
        )
        
        # Guardamos el archivo .mp3 en la carpeta static
        with open(filepath, "wb") as f:
            for chunk in audio_generator:
                if chunk:
                    f.write(chunk)
        return filepath
    except Exception as e:
        # Si escuchas voz de robot, este print te dirá por qué falló ElevenLabs en Render
        print(f"FALLO CRÍTICO ELEVENLABS: {e}")
        return None
