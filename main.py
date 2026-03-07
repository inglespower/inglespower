import os
import requests
import time
from fastapi import FastAPI, Request, WebSocket
from supabase import create_client
from openai import OpenAI

app = FastAPI()

TELNYX_API_KEY = os.getenv("TELNYX_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

VOICE_ID = "21m00Tcm4TlvDq8ikWAM"

client = OpenAI(api_key=OPENAI_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

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

    print("[TELNYX]", r.status_code, path)

    if r.text:
        print(r.text)

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

    url = supabase.storage.from_("audios").get_public_url(path)

    return url


# -------------------------
# WEBHOOK TELNYX
# -------------------------

@app.post("/webhook")
async def webhook(req: Request):

    data = await req.json()

    event = data["data"]["event_type"]
    payload = data["data"]["payload"]

    call_id = payload["call_control_id"]

    print("EVENT:", event)

    # contestar llamada
    if event == "call.initiated":

        telnyx_api(
            f"calls/{call_id}/actions/answer",
            {}
        )

    # llamada contestada
    if event == "call.answered":

        time.sleep(1)

        # iniciar streaming
        telnyx_api(
            f"calls/{call_id}/actions/streaming_start",
            {
                "stream_url": "wss://inglespower.onrender.com/ws"
            }
        )

        # saludo
        audio = generar_audio(
            "Hola, soy tu asistente de inteligencia artificial. ¿En qué puedo ayudarte?"
        )

        url = subir_audio(audio)

        time.sleep(1)

        telnyx_api(
            f"calls/{call_id}/actions/playback_start",
            {
                "audio_url": url
            }
        )

    if event == "call.hangup":

        print("Llamada terminada")

    return {"ok": True}


# -------------------------
# WEBSOCKET STREAM
# -------------------------

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):

    await ws.accept()

    print("Streaming conectado")

    audio_buffer = b""

    while True:

        message = await ws.receive()

        if "bytes" in message:

            audio_buffer += message["bytes"]

        if len(audio_buffer) > 400000:

            filename = f"user_{int(time.time())}.wav"

            with open(filename, "wb") as f:
                f.write(audio_buffer)

            audio_buffer = b""

            with open(filename, "rb") as f:

                transcription = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f
                )

            texto = transcription.text

            print("Usuario:", texto)

            respuesta = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un asistente amable que ayuda por teléfono."
                    },
                    {
                        "role": "user",
                        "content": texto
                    }
                ]
            )

            texto_respuesta = respuesta.choices[0].message.content

            print("AI:", texto_respuesta)

            audio = generar_audio(texto_respuesta)

            url = subir_audio(audio)

            print("Audio respuesta:", url)


# -------------------------
# ROOT
# -------------------------

@app.get("/")
def root():

    return {"status": "running"}
