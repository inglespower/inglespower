import os
import requests
import time
import base64

from fastapi import FastAPI, Request, WebSocket
from supabase import create_client
from openai import OpenAI

app = FastAPI()

# -------------------------
# API KEYS
# -------------------------

TELNYX_API_KEY = os.getenv("TELNYX_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

client = OpenAI(api_key=OPENAI_API_KEY)

VOICE_ID = "21m00Tcm4TlvDq8ikWAM"

# -------------------------
# TELNYX API
# -------------------------

def telnyx_api(path, data):

    url = f"https://api.telnyx.com/v2/{path}"

    headers = {
        "Authorization": f"Bearer {TELNYX_API_KEY}",
        "Content-Type": "application/json"
    }

    r = requests.post(url, headers=headers, json=data)

    print("[TELNYX]", r.status_code)

    return r


# -------------------------
# GENERAR AUDIO
# -------------------------

def generar_audio(texto):

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"

    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "text": texto,
        "model_id": "eleven_multilingual_v2",
        "output_format": "mp3_44100_128"
    }

    r = requests.post(url, headers=headers, json=payload)

    filename = f"tts_{int(time.time())}.mp3"

    with open(filename, "wb") as f:
        f.write(r.content)

    return filename


# -------------------------
# SUBIR AUDIO
# -------------------------

def subir_audio(file):

    path = f"audios/{file}"

    with open(file, "rb") as f:

        supabase.storage.from_("audios").upload(
            path,
            f,
            {"content-type": "audio/mpeg"}
        )

    public = supabase.storage.from_("audios").get_public_url(path)

    return public


# -------------------------
# TRANSCRIBIR AUDIO
# -------------------------

def transcribir(audio_file):

    with open(audio_file, "rb") as f:

        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=f
        )

    return transcription.text


# -------------------------
# WEBHOOK TELNYX
# -------------------------

@app.post("/webhook")
async def webhook(req: Request):

    data = await req.json()

    event = data["data"]["event_type"]
    call = data["data"]["payload"]["call_control_id"]

    print("EVENT:", event)

    if event == "call.initiated":

        telnyx_api(
            f"calls/{call}/actions/answer",
            {}
        )

    if event == "call.answered":

        # iniciar streaming

        telnyx_api(
            f"calls/{call}/actions/streaming_start",
            {
                "stream_url": "wss://TU_DOMINIO/ws"
            }
        )

        # saludo inicial

        audio = generar_audio(
            "Hola, soy tu asistente de inteligencia artificial. ¿En qué puedo ayudarte?"
        )

        url = subir_audio(audio)

        time.sleep(2)

        telnyx_api(
            f"calls/{call}/actions/playback_start",
            {
                "audio_url": url
            }
        )

    return {"ok": True}


# -------------------------
# WEBSOCKET (RECIBE AUDIO)
# -------------------------

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):

    await ws.accept()

    audio_buffer = b""

    while True:

        msg = await ws.receive()

        if "bytes" in msg:

            audio_buffer += msg["bytes"]

        if len(audio_buffer) > 500000:

            file = f"user_{int(time.time())}.wav"

            with open(file, "wb") as f:
                f.write(audio_buffer)

            audio_buffer = b""

            texto = transcribir(file)

            print("USUARIO:", texto)

            respuesta = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "user", "content": texto}
                ]
            )

            texto_respuesta = respuesta.choices[0].message.content

            print("AI:", texto_respuesta)

            audio = generar_audio(texto_respuesta)

            url = subir_audio(audio)

            # reproducir respuesta
            # (necesitas guardar call_control_id global si quieres hacerlo perfecto)
