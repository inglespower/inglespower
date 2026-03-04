import os
import json
import requests
from fastapi import FastAPI, Request, Response
from config import Config
from ai import generar_respuesta
from openai import OpenAI
from supabase import create_client, Client

app = FastAPI()

# Inicializar OpenAI
openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)

# Inicializar Supabase
supabase: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

# Función para llamadas a Telnyx
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

# Función para generar audio ElevenLabs
def generar_audio_elevenlabs(texto):
    try:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{Config.VOICE_ID}/stream?output_format=mp3"
        headers = {"xi-api-key": Config.ELEVENLABS_API_KEY, "Content-Type": "application/json"}
        payload = {"text": texto, "model_id": "eleven_multilingual_v2"}
        res = requests.post(url, json=payload, headers=headers, stream=True)
        if res.status_code == 200:
            audio_path = f"/tmp/tts_{int(os.times().elapsed*1000)}.mp3"
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

# Subir audio a Supabase y obtener URL pública
def subir_audio_supabase(local_path):
    try:
        bucket_name = "audios"
        file_name = os.path.basename(local_path)
        with open(local_path, "rb") as f:
            supabase.storage.from_(bucket_name).upload(file_name, f, {"cacheControl":"3600", "upsert": True})
        public_url = supabase.storage.from_(bucket_name).get_public_url(file_name)
        return public_url
    except Exception as e:
        print(f"[ERR SUPABASE] {e}")
        return None

# Webhook Telnyx
@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        payload = data.get("data", {}).get("payload", {})
        event_type = data.get("data", {}).get("event_type")
        call_id = payload.get("call_control_id")

        # Contestar llamada
        if event_type == "call.initiated" and call_id:
            print(f"[TELNYX] Contestando llamada: {call_id}")
            telnyx_command(f"calls/{call_id}/actions/answer")
            # Iniciar grabación inbound
            telnyx_command(f"calls/{call_id}/actions/record_start", {"direction":"inbound"})

        # Cuando la grabación esté disponible
        elif event_type == "recording.available" and call_id:
            recording_url = payload.get("recording_url")
            if recording_url:
                print(f"[TELNYX] Descargando audio del usuario: {recording_url}")
                audio_res = requests.get(recording_url)
                local_audio_path = f"/tmp/user_audio_{int(os.times().elapsed*1000)}.wav"
                with open(local_audio_path, "wb") as f:
                    f.write(audio_res.content)

                # Transcribir con OpenAI Whisper
                with open(local_audio_path, "rb") as f:
                    transcript = openai_client.audio.transcriptions.create(
                        model="whisper-1",
                        file=f
                    )
                user_text = transcript.text.strip()
                print(f"[USER]: {user_text}")

                # Generar respuesta Thorthugo
                respuesta = generar_respuesta(user_text)
                print(f"[THORTHUGO]: {respuesta}")

                # Generar audio ElevenLabs
                audio_path = generar_audio_elevenlabs(respuesta)
                if audio_path:
                    # Subir a Supabase
                    audio_url = subir_audio_supabase(audio_path)
                    if audio_url:
                        # Reproducir en la llamada
                        play_payload = {"audio_url": audio_url}
                        telnyx_command(f"calls/{call_id}/actions/play_audio", play_payload)

    except Exception as e:
        print(f"[ERROR WEBHOOK] {e}")

    return Response(status_code=200)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
