import os
import requests
import uuid
from openai import OpenAI
from supabase import create_client
from fastapi import FastAPI, Request # O tu framework correspondiente

app = FastAPI()

# 1. CONFIGURACIÓN DE CLIENTES
openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
client = OpenAI(api_key=openai_key)

supabase_url = os.environ.get("SUPABASE_URL", "").strip()
supabase_key = os.environ.get("SUPABASE_KEY", "").strip()
supabase = create_client(supabase_url, supabase_key)

# 2. FUNCIONES DE LÓGICA
def generate_reply(user_text):
    """Genera respuesta con OpenAI (v1.0+)"""
    system_prompt = "You are InglesPower, a bilingual English coach. Be brief."
    try:
        resp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ],
            max_tokens=120
        )
        return resp.choices[0].message.content
    except Exception as e:
        print(f"Error OpenAI: {e}")
        return "Keep going, I'm listening."

def get_nathaniel_voice_url(texto):
    """Convierte texto a audio y sube a Supabase"""
    api_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "").strip()

    if not api_key or not voice_id:
        return None

    url_eleven = f"https://api.elevenlabs.io{voice_id}"
    headers = {"xi-api-key": api_key, "Content-Type": "application/json"}
    data = {
        "text": texto,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
    }

    try:
        response = requests.post(url_eleven, json=data, headers=headers, timeout=30)
        if response.status_code == 200:
            file_name = f"voice_{uuid.uuid4()}.mp3"
            supabase.storage.from_("audios").upload(
                path=file_name,
                file=response.content,
                file_options={"content-type": "audio/mpeg"}
            )
            return supabase.storage.from_("audios").get_public_url(file_name)
    except Exception as e:
        print("Error Voz:", e)
    return None

# 3. WEBHOOK (Aquí estaba el error de indentación de tu imagen)
@app.post("/webhook")
async def whatsapp_webhook(request: Request):
    try:
        # Indentación corregida: 4 espacios
        form_data = await request.form()
        incoming_msg = form_data.get('Body', '').lower()
        
        print(f"Mensaje recibido: {incoming_msg}")
        
        # Aquí llamarías a tus funciones:
        # respuesta = generate_reply(incoming_msg)
        # audio_url = get_nathaniel_voice_url(respuesta)
        
        return {"status": "success"}
    except Exception as e:
        print(f"Error en webhook: {e}")
        return {"status": "error", "message": str(e)}
