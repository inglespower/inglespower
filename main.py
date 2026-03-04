import os
import base64
import requests
from fastapi import FastAPI, Request, Response
from openai import OpenAI
from supabase import create_client, Client
from config import Config
from ai import generar_respuesta

app = FastAPI()

# --- Clientes ---
openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)
supabase: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

# --- Telnyx helper ---
def telnyx_command(endpoint, payload=None):
    url = f"https://api.telnyx.com/v2/{endpoint.lstrip('/')}"
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
        if res.status_code >= 400:
            print("TELNYX ERROR BODY:", res.text)
        return res
    except Exception as e:
        print(f"[ERR TELNYX API] {e}")
        return None

# --- ElevenLabs TTS (ulaw_8000 para Telnyx) ---
def generar_audio_elevenlabs(texto):
    try:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{Config.VOICE_ID}/stream?output_format=ulaw_8000"
        headers = {
            "xi-api-key": Config.ELEVENLABS_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "text": texto,
            "model_id": "eleven_multilingual_v2"
        }

        # IMPORTANTE: stream=True (booleano Python)
        res = requests.post(url, json=payload, headers=headers, stream=True)

        if res.status_code == 200:
            audio_path = f"/tmp/tts_{os.getpid()}_{int(os.times().elapsed*1000)}.ulaw"
            with open(audio_path, "wb") as f:
                for chunk in res.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
            return audio_path
        else:
            print("[ERR VOZ]", res.status_code, res.text)
            return None

    except Exception as e:
        print("[ERR VOZ]", e)
        return None

# --- Subir audio a Supabase ---
def subir_audio_supabase(local_path):
    try:
        bucket_name = "audios"
        file_name = os.path.basename(local_path)

        with open(local_path, "rb") as f:
            supabase.storage.from_(bucket_name).upload(
                file_name,
                f,
                file_options={
                    "cache-control": "3600",
                    "upsert": "true"   # STRING, no true, no True
                }
            )

        public_url = supabase.storage.from_(bucket_name).get_public_url(file_name)
        print("URL PUBLICA:", public_url)
        return public_url

    except Exception as e:
        print("[ERR SUPABASE]", e)
        return None

# --- Webhook Telnyx ---
@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        payload = data.get("data", {}).get("payload", {})
        event_type = data.get("data", {}).get("event_type")
        call_id = payload.get("call_control_id")

        if not call_id:
            return Response(status_code=200)

        # 1️⃣ Llamada iniciada → contestar
        if event_type == "call.initiated":
            print("[TELNYX] Contestando llamada:", call_id)
            telnyx_command(f"calls/{call_id}/actions/answer")

        # 2️⃣ Llamada ya contestada → reproducir bienvenida
        elif event_type == "call.answered":
            print("[TELNYX] Llamada contestada:", call_id)

            bienvenida = (
                "Hola, soy InglesPower. "
                "Pregúntame lo que quieras practicar en inglés."
            )

            audio_path = generar_audio_elevenlabs(bienvenida)

            if audio_path:
                audio_url = subir_audio_supabase(audio_path)
                if audio_url:
                    telnyx_command(
                        f"calls/{call_id}/actions/play_audio",
                        {"audio_url": audio_url}
                    )

        # 3️⃣ Recibiendo audio del usuario
        elif event_type == "call.media.received":
            media_payload = payload.get("media", {})
            chunk_b64 = media_payload.get("payload")

            if chunk_b64:
                audio_bytes = base64.b64decode(chunk_b64)
                tmp_user_audio = "/tmp/user_audio.wav"

                with open(tmp_user_audio, "ab") as f:
                    f.write(audio_bytes)

        # 4️⃣ Usuario terminó de hablar → transcribir y responder
        elif event_type == "call.media.ended":
            tmp_user_audio = "/tmp/user_audio.wav"

            if os.path.exists(tmp_user_audio):
                with open(tmp_user_audio, "rb") as f:
                    transcript = openai_client.audio.transcriptions.create(
                        model="whisper-1",
                        file=f
                    )

                user_text = transcript.text.strip()
                print("[USUARIO]:", user_text)

                if user_text:
                    respuesta = generar_respuesta(user_text)
                    print("[INGLESPOWER]:", respuesta)

                    audio_path = generar_audio_elevenlabs(respuesta)
                    if audio_path:
                        audio_url = subir_audio_supabase(audio_path)
                        if audio_url:
                            telnyx_command(
                                f"calls/{call_id}/actions/play_audio",
                                {"audio_url": audio_url}
                            )

                os.remove(tmp_user_audio)

        elif event_type == "call.hangup":
            print("[TELNYX] Llamada colgada:", call_id)

    except Exception as e:
        print("[ERROR WEBHOOK]", e)

    return Response(status_code=200)


# --- Opcional: ruta raíz para evitar 404 en GET / ---
@app.get("/")
def root():
    return {"status": "InglesPower AI running"}

# --- Run local ---
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
