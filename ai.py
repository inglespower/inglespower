import os
import openai
import requests

def generar_respuesta_ia(texto_usuario):
    """Genera el texto de respuesta usando OpenAI"""
    # Render obtiene esto de tus Environment Variables
    openai.api_key = os.getenv("OPENAI_API_KEY")
    
    system_prompt = "You are InglesPower, a bilingual English coach. Be helpful and brief."
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": texto_usuario}
            ],
            max_tokens=120
        )
        # Acceso correcto al contenido del mensaje
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error en OpenAI: {e}")
        return "I am sorry, I am having a bit of trouble connecting to my brain. Can you repeat that?"

def texto_a_voz_elevenlabs(texto):
    """Convierte el texto en audio (Nathaniel) usando ElevenLabs"""
    api_key = os.getenv("ELEVEN_LABS_API_KEY")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID")
    
    # URL CORREGIDA: Faltaba la ruta completa de la API v1
    url = f"https://api.elevenlabs.io{voice_id}"
    
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    data = {
        "text": texto,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5, 
            "similarity_boost": 0.75 
        }
    }
    
    try:
        # Timeout de 10 segundos para que Telnyx no cuelgue por espera
        response = requests.post(url, json=data, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.content # Devuelve el archivo binario del audio (.mp3)
        else:
            print(f"Error ElevenLabs {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Error de conexión con ElevenLabs: {e}")
        
    return None
