import os
import openai
import requests
import uuid
from supabase import create_client

# 1. CONFIGURACIÓN DE CLIENTES (LIMPIEZA DE ESPACIOS)
openai.api_key = os.environ.get("OPENAI_API_KEY", "").strip()
supabase_url = os.environ.get("SUPABASE_URL", "").strip()
supabase_key = os.environ.get("SUPABASE_KEY", "").strip()

if not supabase_url or not supabase_key:
    raise ValueError("Error: Faltan SUPABASE_URL o SUPABASE_KEY en Render.")

supabase = create_client(supabase_url, supabase_key)

def generate_reply(user_text):
    system = "You are InglesPower, a bilingual English coach. Be brief."
    try:
        # Formato compatible con openai==0.28
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user_text}],
            max_tokens=120
        )
        return resp.choices[0].message.content
    except Exception as e:
        print(f"Error OpenAI: {e}")
        return "Keep going, I'm listening."

def get_nathaniel_voice_url(texto):
    api_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "").strip()
    
    # --- CORRECCIÓN CRÍTICA AQUÍ ---
    # La URL DEBE tener la ruta completa para que ElevenLabs la reconozca
    url_eleven = f"https://api.elevenlabs.io{voice_id}"
    
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
        # Se aumentó el timeout a 30 para evitar cortes en audios largos
        response = requests.post(url_eleven, json=data, headers=headers, timeout=30)
        
        if response.status_code == 200:
            file_name = f"voice_{uuid.uuid4()}.mp3"
            
            # Subida al bucket "audios"
            supabase.storage.from_("audios").upload(
                path=file_name, 
                file=response.content, 
                file_options={"content-type": "audio/mpeg"}
            )
            
            # Obtener URL pública (Asegúrate que el bucket 'audios' sea público en Supabase)
            return supabase.storage.from_("audios").get_public_url(file_name)
        else:
            print(f"Error ElevenLabs: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"Error Voz Nathaniel: {e}")
    return None
