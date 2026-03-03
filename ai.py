from openai import OpenAI
from elevenlabs.client import ElevenLabs # Importamos el cliente oficial
from config import Config

# Clientes
client_openai = OpenAI(api_key=Config.OPENAI_API_KEY)

# INICIALIZACIÓN CORREGIDA
# Usamos el cliente directamente para acceder a sus métodos
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
                        "Explica brevemente en español y da el ejemplo en inglés. Máximo 2 frases."
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
    """Genera audio con la sintaxis correcta del SDK v1.0.0+."""
    try:
        # SINTAXIS CORREGIDA: Se accede a través de client_el.generate
        audio_generator = client_el.generate(
            text=texto,
            voice=Config.ELEVENLABS_VOICE_ID, 
            model="eleven_multilingual_v2"
        )
        
        # Guardamos el archivo .mp3
        with open(filepath, "wb") as f:
            # ElevenLabs devuelve un generador de bytes
            for chunk in audio_generator:
                if chunk:
                    f.write(chunk)
        return filepath
    except Exception as e:
        # Si esto falla, el log de Render nos dirá si es por SALDO o por la API KEY
        print(f"FALLO CRÍTICO ELEVENLABS: {e}")
        return None
