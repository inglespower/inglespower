import os
import json
import uuid
import asyncio
import websockets
import requests
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from openai import OpenAI

app = FastAPI()

# -----------------------------
# Configuración de APIs
# -----------------------------
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
TELNYX_API_KEY = os.environ.get("TELNYX_API_KEY")

openai_client = OpenAI(api_key=OPENAI_API_KEY)

# -----------------------------
# Variables globales
# -----------------------------
active_calls = {}  # {call_id: websocket}

# -----------------------------
# Página de prueba
# -----------------------------
@app.get("/")
async def root():
    return {"status": "Server running"}

# -----------------------------
# Webhook Telnyx para llamadas
# -----------------------------
@app.post("/webhook")
async def telnyx_webhook(request: dict):
    event_type = request.get("event_type")
    call_id = request.get("data", {}).get("id")

    if event_type == "call.initiated":
        # Contestar la llamada
        url = f"https://api.telnyx.com/v2/calls/{call_id}/actions/answer"
        headers = {"Authorization": f"Bearer {TELNYX_API_KEY}"}
        requests.post(url, headers=headers)

    elif event_type == "call.answered":
        # Iniciar gather streaming
        url = f"https://api.telnyx.com/v2/calls/{call_id}/actions/start_audio_stream"
        headers = {
            "Authorization": f"Bearer {TELNYX_API_KEY}",
            "Content-Type": "application/json"
        }
        ws_session_id = str(uuid.uuid4())
        body = {
            "stream_url": f"wss://{os.environ.get('HOSTNAME', 'tu_dominio')}/ws/{call_id}",
            "audio_format": "linear16"
        }
        requests.post(url, headers=headers, json=body)

        # Enviar primer TTS al usuario
        text = "Hola, soy InglesPower. ¿Qué quieres aprender hoy? Puedes hablar y te responderé en inglés."
        await send_tts_to_telnyx(call_id, text)

    elif event_type == "call.hangup":
        if call_id in active_calls:
            ws = active_calls[call_id]
            await ws.close()
            del active_calls[call_id]
        print(f"Llamada {call_id} finalizada")

    return {"status": "ok"}

# -----------------------------
# WebSocket para recibir audio
# -----------------------------
@app.websocket("/ws/{call_id}")
async def audio_stream(websocket: WebSocket, call_id: str):
    await websocket.accept()
    active_calls[call_id] = websocket
    print(f"WebSocket abierto para llamada {call_id}")

    audio_buffer = bytearray()
    try:
        while True:
            data = await websocket.receive_bytes()
            # Guardamos el audio recibido
            audio_buffer.extend(data)

            # Cada 5 segundos procesamos el audio
            if len(audio_buffer) > 16000 * 5 * 2:  # 5s de audio mono 16bit
                transcript = await speech_to_text(audio_buffer)
                audio_buffer = bytearray()  # vaciar buffer

                if transcript:
                    print(f"Transcripción: {transcript}")
                    reply_text = await generate_openai_reply(transcript)
                    await send_tts_to_telnyx(call_id, reply_text)

    except WebSocketDisconnect:
        print(f"WebSocket cerrado para llamada {call_id}")
        if call_id in active_calls:
            del active_calls[call_id]

# -----------------------------
# Función para convertir audio a texto usando OpenAI
# -----------------------------
async def speech_to_text(audio_bytes: bytes):
    # Guardamos el audio temporalmente
    tmp_file = f"/tmp/{uuid.uuid4()}.wav"
    with open(tmp_file, "wb") as f:
        f.write(audio_bytes)

    with open(tmp_file, "rb") as f:
        transcript = openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=f
        )
    return transcript.text

# -----------------------------
# Función para generar respuesta en inglés usando OpenAI
# -----------------------------
async def generate_openai_reply(user_text: str):
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Eres un asistente que enseña inglés de forma clara y sencilla."},
            {"role": "user", "content": user_text}
        ]
    )
    return response.choices[0].message.content

# -----------------------------
# Función para enviar TTS a Telnyx usando ElevenLabs
# -----------------------------
async def send_tts_to_telnyx(call_id: str, text: str):
    # Convertir texto a audio
    tts_url = "https://api.elevenlabs.io/v1/text-to-speech/EXAVITQu4vr4xnSDxMaL/stream"
    headers = {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}
    body = {"text": text, "voice_settings": {"stability":0.7,"similarity_boost":0.8}}
    resp = requests.post(tts_url, headers=headers, json=body)

    # Enviar audio a Telnyx
    play_url = f"https://api.telnyx.com/v2/calls/{call_id}/actions/play_audio"
    files = {"file": ("response.mp3", resp.content, "audio/mpeg")}
    play_headers = {"Authorization": f"Bearer {TELNYX_API_KEY}"}
    requests.post(play_url, headers=play_headers, files=files)
