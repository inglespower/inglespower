import os
import openai
import requests
import uuid
from supabase import create_client

# Configuración de Clientes
openai.api_key = os.getenv("OPENAI_API_KEY")
supabase_url = os.getenv("SUPABASE_URL")
# Usa la 'service_role' key en Render para tener permisos de subida
supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") 
supabase = create_client(supabase_url, supabase_key)

def generate_reply(user_text):
    system = "You are InglesPower, a bilingual English coach. Be brief."
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user_text}],
            max_tokens=120
        )
        return resp.choices[0].message.content
    except:
        return "Keep going, I'm listening."

def get_nathaniel_voice_url(texto):
    api_key = os.getenv("ELEVEN_LABS_API_KEY")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID")
    url_eleven = f"https://api.elevenlabs.io{voice_id}"
    
    headers = {"xi-api-key": api_key, "Content-Type": "application/json"}
    data = {
        "text": texto,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
    }
    
    try:
        # 1. Pedir audio a ElevenLabs
        response = requests.post(url_eleven, json=data, headers=headers, timeout=10)
        if response.status_code == 200:
            # 2. Generar nombre único y subir a Supabase
            file_name = f"voice_{uuid.uuid4()}.mp3"
            supabase.storage.from_("audios").upload(
                path=file_name, 
                file=response.content, 
                file_options={"content-type": "audio/mpeg"}
            )
            # 3. Devolver la URL pública para Telnyx
            return supabase.storage.from_("audios").get_public_url(file_name)
    except Exception as e:
        print(f"Error Voz: {e}")
    return None
