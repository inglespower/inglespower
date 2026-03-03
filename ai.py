from openai import OpenAI
from elevenlabs.client import ElevenLabs # Importación del cliente v1.x
from config import Config

# Inicialización de clientes
client_openai = OpenAI(api_key=Config.OPENAI_API_KEY)

# IMPORTANTE: Inicializamos el cliente con un nombre distinto (client_el)
client_el = ElevenLabs(api_key=Config.ELEVENLABS_API_KEY)

def generar_respuesta(texto_usuario):
    """Genera respuesta breve del tutor en ESPAÑOL."""
    try:
        response = client_openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system", 
                    "content": (
                        "Eres un tutor de inglés nativo. REGLA DE ORO: RESPONDE SIEMPRE EN ESPAÑOL. "
                        "Sé amable y muy breve (máximo 2 frases). "
                        "Explica en español y da el ejemplo en inglés."
                    )
                },
                {"role": "user", "content": texto_usuario}
            ]
        )
        return response.choices.message.content
    except Exception as e:
        print(f"Error OpenAI: {e}")
        return "Lo siento, tuve un problema. ¿Puedes repetir?"

def texto_a_voz(texto, filepath):
    """Convierte texto a audio con la SINTAXIS CORREGIDA para SDK v1+."""
    try:
        # CORRECCIÓN DEFINITIVA: Se usa client_el.generate
        audio_generator = client_el.generate(
            text=texto,
            voice=Config.ELEVENLABS_VOICE_ID, 
            model="eleven_multilingual_v2"
        )
        
        # Guardamos el archivo físico en el servidor
        with open(filepath, "wb") as f:
            for chunk in audio_generator:
                if chunk:
                    f.write(chunk)
        return filepath
    except Exception as e:
        # Si esto falla, el log de Render dirá la razón real
        print(f"FALLO REAL ELEVENLABS: {e}")
        return None
