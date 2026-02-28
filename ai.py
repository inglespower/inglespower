import os
import openai
import requests

def generar_respuesta_ia(texto_usuario):
    # Usamos os.getenv para que Render lea las variables que configuramos
    openai.api_key = os.getenv("OPENAI_API_KEY")
    
    # Mantenemos tu personalidad de InglesPower
    system_prompt = "You are InglesPower, a bilingual English coach..."
    
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": texto_usuario}
        ],
        max_tokens=120
    )
    # Corregido: añadimos [0] para acceder al primer mensaje
    return response.choices[0].message.content

def texto_a_voz_elevenlabs(texto):
    api_key = os.getenv("ELEVEN_LABS_API_KEY")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID")
    
    # CORRECCIÓN DE URL: Faltaba la ruta completa a la API
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
            "similarity_boost": 0.75 # Un poco más de claridad para llamadas
        }
    }
    
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            return response.content 
    except Exception as e:
        print(f"Error en ElevenLabs: {e}")
        
    return None
