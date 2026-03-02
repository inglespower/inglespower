import os
import uuid
import requests
from fastapi import FastAPI, Request, BackgroundTasks
from openai import OpenAI
from supabase import create_client

app = FastAPI()

# 1. CONFIGURACIÓN DE CLIENTES
openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
client = OpenAI(api_key=openai_key)

supabase_url = os.environ.get("SUPABASE_URL", "").strip()
supabase_key = os.environ.get("SUPABASE_KEY", "").strip()
supabase = create_client(supabase_url, supabase_key)

# 2. FUNCIONES DE LÓGICA (PROCESOS PESADOS)
def generate_reply(user_text):
    """Genera respuesta de texto con OpenAI"""
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
        # Corrección para OpenAI v1.0+: se accede con .content
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

    # URL CORREGIDA: Evita el error de resolución de nombre
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
            public_url = supabase.storage.from_("audios").get_public_url(file_name)
            print(f"Audio generado exitosamente: {public_url}")
            return public_url
    except Exception as e:
        print(f"Error Voz: {e}")
    return None

# 3. TAREA EN SEGUNDO PLANO
def handle_full_process(user_msg):
    """Ejecuta la IA y la Voz sin bloquear la respuesta del servidor"""
    texto = generate_reply(user_msg)
    audio = get_nathaniel_voice_url(texto)
    # Aquí es donde podrías guardar el resultado en una base de datos 
    # para que tu App lo lea cuando esté listo.
    print(f"Proceso de fondo terminado para: {user_msg}")

# 4. ENDPOINT WEBHOOK (RÁPIDO)
@app.post("/webhook")
async def process_message(request: Request, background_tasks: BackgroundTasks):
    try:
        # Detectar si viene como Formulario o JSON
        form_data = await request.form()
        if form_data:
            user_msg = form_data.get('Body') or form_data.get('text', '')
        else:
            json_data = await request.json()
            user_msg = json_data.get('text', '')

        if not user_msg:
            return {"status": "error", "message": "No text received"}

        print(f"Recibido: {user_msg}. Procesando en segundo plano...")
        
        # LANZAR PROCESO PESADO AL FONDO: Esto evita que Render corte por tiempo
        background_tasks.add_task(handle_full_process, user_msg)
        
        # Responder de inmediato (esto evita el corte de conexión)
        return {
            "status": "processing",
            "message": "Estamos preparando tu respuesta de audio."
        }

    except Exception as e:
        print(f"Error Webhook: {e}")
        return {"status": "error", "detail": str(e)}

@app.get("/")
async def root():
    return {"status": "InglesPower Coach is active!"}
