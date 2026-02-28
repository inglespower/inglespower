import os
import openai
import requests

# Esta es la función que tu main.py llama
def generate_reply(user_text):
    openai.api_key = os.getenv("OPENAI_API_KEY")
    
    # Tu prompt original de InglesPower
    system = "You are InglesPower, a bilingual English coach..."
    
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_text}
            ],
            max_tokens=120
        )
        return resp.choices[0].message.content
    except Exception as e:
        print(f"Error en OpenAI: {e}")
        return "I'm sorry, can you repeat that?"

# Esta es la que usaremos después para Nathaniel
def texto_a_voz_elevenlabs(texto):
    api_key = os.getenv("ELEVEN_LABS_API_KEY")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID")
    
    # URL CORREGIDA: Esto es lo que hacía que se cortara
    url = f"https://api.elevenlabs.io{voice_id}"
    
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    data = {
        "text": texto,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
    }
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=8)
        if response.status_code == 200:
            return response.content 
    except:
        pass
    return None
