import os
import uuid
import asyncio
import requests
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from openai import OpenAI

app = FastAPI()

# -----------------------------
# API KEYS
# -----------------------------
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
TELNYX_API_KEY = os.environ.get("TELNYX_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# -----------------------------
# CONFIG
# -----------------------------
PUBLIC_URL = "https://inglespower.onrender.com"

active_calls = {}

# -----------------------------
# TEST ENDPOINT
# -----------------------------
@app.get("/")
async def root():
    return {"status": "server running"}

# -----------------------------
# TELNYX WEBHOOK
# -----------------------------
@app.post("/webhook")
async def webhook(request: Request):

    body = await request.json()
    event = body.get("event_type")
    call_id = body.get("data", {}).get("id")

    print("EVENT:", event)

    # -----------------------------
    # CALL START
    # -----------------------------
    if event == "call.initiated":

        requests.post(
            f"https://api.telnyx.com/v2/calls/{call_id}/actions/answer",
            headers={"Authorization": f"Bearer {TELNYX_API_KEY}"}
        )

    # -----------------------------
    # CALL ANSWERED
    # -----------------------------
    elif event == "call.answered":

        # SALUDO INICIAL
        await speak(call_id,
        "Hola soy InglesPower. Puedes preguntarme cualquier cosa para aprender inglés.")

        # INICIAR STREAM
        requests.post(
            f"https://api.telnyx.com/v2/calls/{call_id}/actions/start_audio_stream",
            headers={
                "Authorization": f"Bearer {TELNYX_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "stream_url": f"wss://inglespower.onrender.com/ws/{call_id}",
                "audio_format": "linear16"
            }
        )

    # -----------------------------
    # CALL END
    # -----------------------------
    elif event == "call.hangup":

        print("Llamada terminada")

        if call_id in active_calls:
            del active_calls[call_id]

    return {"ok": True}

# -----------------------------
# WEBSOCKET AUDIO STREAM
# -----------------------------
@app.websocket("/ws/{call_id}")
async def websocket_audio(websocket: WebSocket, call_id: str):

    await websocket.accept()
    active_calls[call_id] = websocket

    print("WebSocket conectado:", call_id)

    buffer = bytearray()

    try:

        while True:

            data = await websocket.receive_bytes()
            buffer.extend(data)

            # procesar cada 0.5 segundos
            if len(buffer) > 16000:

                audio = buffer
                buffer = bytearray()

                asyncio.create_task(process_audio(audio, call_id))

    except WebSocketDisconnect:

        print("WebSocket cerrado")

        if call_id in active_calls:
            del active_calls[call_id]

# -----------------------------
# PROCESS AUDIO
# -----------------------------
async def process_audio(audio, call_id):

    text = await speech_to_text(audio)

    if not text:
        return

    print("USUARIO:", text)

    response = await ask_ai(text)

    print("AI:", response)

    await speak(call_id, response)

# -----------------------------
# SPEECH TO TEXT
# -----------------------------
async def speech_to_text(audio):

    filename = f"/tmp/{uuid.uuid4()}.wav"

    with open(filename, "wb") as f:
        f.write(audio)

    with open(filename, "rb") as f:

        result = client.audio.transcriptions.create(
            model="whisper-1",
            file=f
        )

    return result.text

# -----------------------------
# OPENAI RESPONSE
# -----------------------------
async def ask_ai(text):

    completion = client.chat.completions.create(

        model="gpt-4o-mini",

        messages=[

            {
                "role": "system",
                "content":
                "Eres un profesor amigable que enseña inglés a hispanohablantes."
            },

            {
                "role": "user",
                "content": text
            }

        ]

    )

    return completion.choices[0].message.content

# -----------------------------
# TEXT TO SPEECH
# -----------------------------
async def speak(call_id, text):

    if not text:
        return

    audio = requests.post(

        "https://api.elevenlabs.io/v1/text-to-speech/EXAVITQu4vr4xnSDxMaL",

        headers={
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json"
        },

        json={
            "text": text
        }

    )

    files = {
        "file": ("audio.mp3", audio.content, "audio/mpeg")
    }

    requests.post(

        f"https://api.telnyx.com/v2/calls/{call_id}/actions/play_audio",

        headers={
            "Authorization": f"Bearer {TELNYX_API_KEY}"
        },

        files=files

    )

# -----------------------------
# START SERVER
# -----------------------------
if __name__ == "__main__":

    port = int(os.environ.get("PORT", 10000))

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port
    )
