import base64
import json
import httpx
import openai
from config import Config

openai.api_key = Config.OPENAI_API_KEY

SYSTEM_PROMPT = (
    "Eres un tutor de inglés nativo y paciente. Tu objetivo es ayudar al usuario a practicar. "
    "Mantén tus respuestas cortas (máximo 2 oraciones) para que la conversación sea fluida por teléfono. "
    "Si el usuario comete un error, corrígelo suavemente."
)

async def procesar_voz_a_voz(audio_base64_incoming):
    """
    Recibe audio de Telnyx, le pregunta a OpenAI y devuelve audio de ElevenLabs.
    """
    # 1. Convertir audio entrante a texto (Whisper)
    # (En una implementación de baja latencia, esto se hace via Streaming WebSocket)
    # Aquí simulamos el flujo de respuesta de texto a voz:
    
    texto_usuario = "Hello, I want to practice my English." # Simulación de entrada
    
    # 2. Generar respuesta de texto con GPT-4o
    response = await openai.ChatCompletion.acreate(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": texto_usuario}
        ]
    )
    respuesta_texto = response.choices[0].message.content

    # 3. Convertir esa respuesta a voz humana con ElevenLabs
    headers = {
        "xi-api-key": Config.ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "text": respuesta_texto,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.8}
    }

    url = f"https://api.elevenlabs.io{Config.ELEVENLABS_VOICE_ID}"
    
    async with httpx.AsyncClient() as client:
        res = await client.post(url, json=payload, headers=headers)
        if res.status_code == 200:
            # Convertimos el audio binario a Base64 para que Telnyx lo pueda reproducir
            audio_base64 = base64.b64encode(res.content).decode('utf-8')
            return audio_base64
    return None
