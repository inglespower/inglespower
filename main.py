import os
import base64
import requests
from fastapi import FastAPI, Request, Response
from config import Config
from ai import generar_respuesta
from openai import OpenAI
from supabase import create_client, Client

app = FastAPI()

# Inicialización OpenAI
openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)

# Inicialización Supabase
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
        print(f"[TELNYX API] Status: {res.status_code} -> {url}")
        if res.status_code >= 400:
            print(f"[TELNYX ERROR BODY]: {res.text}")
        return res
    except Exception as e:
        print(f"[ERR TELNYX API] {e}")
        return None

# Función para generar audio ElevenLabs (µ-law 8kHz)
def generar_audio_elevenlabs(texto):
    try:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{Config.VOICE_ID}/stream?output_format=ulaw_8000"
        headers = {
            "xi-api-key": Config.ELEVENLABS_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {"text": texto, "model_id": "eleven_multilingual_v2"}
        res = requests.post(url, json=payload, headers=headers, stream=True)
        if res.status_code == 200:
            audio_path = f"/tmp/tts_{int(os.times().elapsed*1000)}.ulaw"
            with open(audio_path, "wb") as f:
                for chunk in res.iter_content(1024):
                    if chunk:
                        f.write(chunk)
            return audio_path
        else:
            print(f"[ERR VOZ] Status {res.status_code}, {res.text}")
            return None
    except Exception as e:
        print(f"[ERR VOZ] {e}")
        return None

# Subir audio a Supabase
def subir_audio_supabase(local_path):
    try:
        bucket_name = "audios"
        file_name = os.path.basename(local_path)
        with open(local_path, "rb") as f:
            supabase.storage.from_(bucket_name).upload(file_name, f, {"cacheControl": "3600", "upsert": True})
        public_url = supabase.storage.from_(bucket_name).get_public_url(file_name)
        return public_url
    except Exception as e:
        print(f"[ERR SUPABASE] {e}")
        return None

# Enviar audio chunk a Telnyx
def enviar_audio_chunks(call_id, audio_path, chunk_size=1024):
    try:
        with open(audio_path, "rb") as f:
            while chunk := f.read(chunk_size):
                audio_b64 = base64.b64encode(chunk).decode("utf-8")
                telnyx_command(f"calls/{call_id}/actions/send_audio", {"audio_chunk": audio_b64})
    except Exception as e:
        print(f"[ERR STREAM] {e}")

# Webhook Telnyx
@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        payload = data.get("data", {}).get("payload", {})
        event_type = data.get("data", {}).get("event_type")
        call_id = payload.get("call_control_id")

        if event_type == "call.initiated" and call_id:
            print(f"[TELNYX] Contestando llamada: {call_id}")
            telnyx_command(f"calls/{call_id}/actions/answer")

            # Reproducir bienvenida
            bienvenida = "¡Hola! Soy InglesPower, tu asistente para aprender inglés. Pregúntame lo que quieras."
            audio_path = generar_audio_elevenlabs(bienvenida)
            if audio_path:
                audio_url = subir_audio_supabase(audio_path)
                if audio_url:
                    # Enviar en chunks RAW µ-law a Telnyx
                    enviar_audio_chunks(call_id, audio_path)

        elif event_type == "call.media.received" and call_id:
            media_payload = payload.get("media", {})
            chunk_b64 = media_payload.get("payload")
            if chunk_b64:
                audio_bytes = base64.b64decode(chunk_b64)
                tmp_user_audio = "/tmp/user_audio.wav"
                with open(tmp_user_audio, "ab") as f:
                    f.write(audio_bytes)

        elif event_type == "call.media.ended" and call_id:
            tmp_user_audio = "/tmp/user_audio.wav"
            if os.path.exists(tmp_user_audio):
                with open(tmp_user_audio, "rb") as f:
                    transcript = openai_client.audio.transcriptions.create(
                        model="whisper-1",
                        file=f
                    )
                user_text = transcript.text.strip()
                print(f"[USUARIO]: {user_text}")
                if user_text:
                    respuesta = generar_respuesta(user_text)
                    print(f"[INGLESPOWER]: {respuesta}")
                    audio_path = generar_audio_elevenlabs(respuesta)
                    if audio_path:
                        audio_url = subir_audio_supabase(audio_path)
                        if audio_url:
                            enviar_audio_chunks(call_id, audio_path)
                os.remove(tmp_user_audio)

        elif event_type == "call.hangup" and call_id:
            print(f"[TELNYX] Llamada colgada: {call_id}")

    except Exception as e:
        print(f"[ERROR WEBHOOK] {e}")
    return Response(status_code=200)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
