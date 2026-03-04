import os
import json
import time
import threading
import requests
from fastapi import FastAPI, Request, Response
from config import Config
from ai import generar_respuesta
from openai import OpenAI
from supabase import create_client, Client

app = FastAPI()

# Inicialización
openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)
supabase: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

def telnyx_command(endpoint, payload=None):
    base_url = "https://api.telnyx.com/v2/"
    url = f"{base_url}{endpoint.lstrip('/')}"
    headers = {
        "Authorization": f"Bearer {Config.TELNYX_API_KEY}",
        "Content-Type": "application/json"
    }
    try:
        if payload:
            res = requests.post(url, json=payload, headers=headers)
        else:
            res = requests.post(url, headers=headers)
        print(f"[TELNYX API] Status: {res.status_code} para {url}")
        return res
    except Exception as e:
        print(f"[ERR TELNYX API] Error de conexión a {url}: {e}")
        return None

def generar_audio_elevenlabs(texto):
    try:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{Config.VOICE_ID}/stream?output_format=ulaw_8000"
        headers = {"xi-api-key": Config.ELEVENLABS_API_KEY, "Content-Type": "application/json"}
        payload = {"text": texto, "model_id": "eleven_multilingual_v2"}
        res = requests.post(url, json=payload, headers=headers, stream=True)
        if res.status_code == 200:
            audio_path = f"/tmp/tts_{int(os.times().elapsed*1000)}.ulaw"
            with open(audio_path, "wb") as f:
                for chunk in res.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
            return audio_path
        else:
            print(f"[ERR VOZ] Status {res.status_code}, {res.text}")
            return None
    except Exception as e:
        print(f"[ERR VOZ] {e}")
        return None

def subir_audio_supabase(local_path):
    try:
        bucket_name = "audios"
        file_name = os.path.basename(local_path)
        with open(local_path, "rb") as f:
            supabase.storage.from_(bucket_name).upload(
                file_name,
                f,
                {"cacheControl":"3600", "upsert":"true"}
            )
        public_url = supabase.storage.from_(bucket_name).get_public_url(file_name)
        return public_url
    except Exception as e:
        print(f"[ERR SUPABASE] {e}")
        return None

def play_audio_telnyx(call_id, audio_url):
    payload = {"audio_url": audio_url}
    telnyx_command(f"calls/{call_id}/actions/play_audio", payload)

def procesar_usuario_audio(call_id, recording_url):
    try:
        audio_res = requests.get(recording_url)
        local_audio_path = f"/tmp/user_audio_{int(os.times().elapsed*1000)}.wav"
        with open(local_audio_path, "wb") as f:
            f.write(audio_res.content)

        with open(local_audio_path, "rb") as f:
            transcript = openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=f
            )
        user_text = transcript.text.strip()
        print(f"[USER]: {user_text}")

        respuesta = generar_respuesta(user_text)
        print(f"[INGLESPOWER]: {respuesta}")

        audio_path = generar_audio_elevenlabs(respuesta)
        if audio_path:
            audio_url = subir_audio_supabase(audio_path)
            if audio_url:
                play_audio_telnyx(call_id, audio_url)
    except Exception as e:
        print(f"[ERROR PROCESAR AUDIO] {e}")

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        payload = data.get("data", {}).get("payload", {})
        event_type = data.get("data", {}).get("event_type")
        call_id = payload.get("call_control_id")

        if not call_id:
            return Response(status_code=400)

        if event_type == "call.initiated":
            print(f"[TELNYX] Contestando llamada: {call_id}")
            telnyx_command(f"calls/{call_id}/actions/answer")

        elif event_type == "call.answered":
            print(f"[TELNYX] Reproduciendo bienvenida: {call_id}")
            bienvenida = (
                "¡Hola! Soy InglesPower, tu mejor recurso para aprender inglés. "
                "Pregúntame lo que quieras o dime qué quieres aprender hoy."
            )
            audio_path = generar_audio_elevenlabs(bienvenida)
            if audio_path:
                audio_url = subir_audio_supabase(audio_path)
                if audio_url:
                    play_audio_telnyx(call_id, audio_url)

        elif event_type == "recording.available":
            recording_url = payload.get("recording_url")
            if recording_url:
                threading.Thread(
                    target=procesar_usuario_audio,
                    args=(call_id, recording_url),
                    daemon=True
                ).start()

        elif event_type == "call.hangup":
            print(f"[TELNYX] Llamada colgada: {call_id}")

    except Exception as e:
        print(f"[ERROR WEBHOOK] {e}")

    return Response(status_code=200)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
