import base64
import httpx
import openai
from config import Config

# Configuración de OpenAI
openai.api_key = Config.OPENAI_API_KEY

SYSTEM_PROMPT = (
    "Eres un tutor de inglés nativo y paciente. Tu misión es ayudar al usuario a practicar. "
    "Responde de forma breve (máximo 2 frases) para que la conversación sea fluida por teléfono. "
    "Si el usuario comete un error, corrígelo suavemente en inglés."
)

async def generar_respuesta_ia(texto_usuario):
    """Pregunta a GPT-4o y obtiene respuesta de texto"""
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": texto_usuario}
            ],
            max_tokens=100
        )
        return response.choices.message.content
    except Exception as e:
        print(f"Error OpenAI: {e}")
        return "I'm sorry, could you repeat that?"

async def voz_eleven_labs(texto):
    """Convierte el texto en audio de alta calidad (Voz humana)"""
    url = f"https://api.elevenlabs.io{Config.ELEVENLABS_VOICE_ID}"
    headers = {
        "xi-api-key": Config.ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "text": texto,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5, 
            "similarity_boost": 0.8
        }
    }
    async with httpx.AsyncClient() as client:
        res = await client.post(url, json=data, headers=headers)
        if res.status_code == 200:
            # Retorna el audio codificado en Base64 para que Telnyx lo reproduzca
            return base64.b64encode(res.content).decode('utf-8')
    return None
