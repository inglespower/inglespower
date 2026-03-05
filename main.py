import os
import io
import base64
import wave
import time
import requests
from fastapi import FastAPI, Request, Response
from config import Config
from ai import generar_respuesta  # Tu función que genera la respuesta
from openai import OpenAI

app = FastAPI()

# Inicialización OpenAI
openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)

# ---------------------
# Función Telnyx API
# ---------------------
def telnyx_command(endpoint, payload=None):
    base_url = "https://api.telnyx.com/v2/"
    url = f"{base_url}{endpoint.lstrip('/')}"
    headers = {
        "Authorization": f"Bearer {Config.TELNYX_API_KEY}",
        "Content-Type": "application/json"
    }
    try:
        res = requests.post(url, json=payload, headers=headers) if payload else requests.post(url, headers=headers)
        print(f"[TELNYX API] Status: {res.status_code} -> {url}")
        if res.status_code not in [200, 202]:
            print(res.text)
        return res
    except Exception as e:
        print(f"[ERR TELNYX API] {e}")
        return None

# ---------------------
# Generar audio ElevenLabs
# ---------------------
def generar_audio_elevenlabs(texto, output_path="/tmp/tts_output.ulaw"):
    try:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{Config.VOICE_ID}/stream?output_format=ulaw_8000"
        headers = {"xi-api-key": Config.ELEVENLABS_API_KEY, "Content-Type": "application/json"}
        payload = {"text": texto, "model_id": "eleven_multilingual_v2"}
        with requests.post(url, json=payload, headers=headers, stream=True) as res:
            if res.status_code == 200:
                with open(output_path, "wb") as f:
                    for chunk in res.iter_content(chunk_size=1024):
                        if chunk:
                            f.write(chunk)
                return output_path
            else:
                print(f"[ERR VOZ] Status {res.status_code}: {res.text}")
                return None
    except Exception as e:
        print(f"[ERR VOZ] {e}")
        return None

# ---------------------
# Enviar audio a Telnyx en chunks
# ---------------------
def enviar_audio_chunks(call_id, audio_path, chunk_ms=40):
    """Envía audio WAV 8kHz u-law a Telnyx Media Streams"""
    try:
        with wave.open(audio_path, 'rb') as wf:
            framerate = wf.getframerate()
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            frames_per_chunk = int(framerate * chunk_ms / 1000)
            total_frames = wf.getnframes()
            
            while True:
                frames = wf.readframes(frames_per_chunk)
                if not frames:
                    break
                audio_b64 = base64.b64encode(frames).decode('utf-8')
                telnyx_command(f"calls/{call_id}/actions/send_audio", {"audio_chunk": audio_b64})
                time.sleep(chunk_ms / 1000)  # ritmo real-time
    except Exception as e:
        print(f"[ERR STREAM] {e}")

# ---------------------
# Webhook Telnyx
# ---------------------
@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        payload = data.get("data", {}).get("payload", {})
        event_type = data.get("data", {}).get("event_type")
        call_id = payload.get("call_control_id")
        
        if not call_id:
            return Response(status_code=200)

        # ---------------------
        # Llamada iniciada → contestar
        # ---------------------
        if event_type == "call.initiated":
            print(f"[TELNYX] Contestando llamada: {call_id}")
            telnyx_command(f"calls/{call_id}/actions/answer")
            
            # Generar bienvenida y enviar en streaming
            bienvenida = "¡Hola! Soy tu asistente de inglés. Pregúntame lo que quieras."
            audio_path = generar_audio_elevenlabs(bienvenida)
            if audio_path:
                enviar_audio_chunks(call_id, audio_path)

        # ---------------------
        # Audio recibido
        # ---------------------
        elif event_type == "call.media.received":
            media_payload = payload.get("media", {})
            chunk_b64 = media_payload.get("payload")
            if chunk_b64:
                audio_bytes = base64.b64decode(chunk_b64)
                tmp_path = "/tmp/user_audio.wav"
                with open(tmp_path, "ab") as f:
                    f.write(audio_bytes)

        # ---------------------
        # Fin del audio del usuario → transcribir y responder
        # ---------------------
        elif event_type == "call.media.ended":
            tmp_path = "/tmp/user_audio.wav"
            if os.path.exists(tmp_path):
                with open(tmp_path, "rb") as f:
                    transcript = openai_client.audio.transcriptions.create(
                        model="whisper-1",
                        file=f
                    )
                user_text = transcript.text.strip()
                print(f"[USUARIO]: {user_text}")

                if user_text:
                    respuesta = generar_respuesta(user_text)
                    print(f"[ASISTENTE]: {respuesta}")
                    audio_path = generar_audio_elevenlabs(respuesta)
                    if audio_path:
                        enviar_audio_chunks(call_id, audio_path)

                os.remove(tmp_path)

        # ---------------------
        # Llamada colgada
        # ---------------------
        elif event_type == "call.hangup":
            print(f"[TELNYX] Llamada colgada: {call_id}")

    except Exception as e:
        print(f"[ERROR WEBHOOK] {e}")
    return Response(status_code=200)

# ---------------------
# Arranque
# ---------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
