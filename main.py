import os
import uuid
import asyncio
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
# Endpoint de prueba
# -----------------------------
@app.get("/")
async def root():
    return {"status": "Server running"}

# -----------------------------
# Webhook Telnyx
# -----------------------------
@app.post("/webhook")
async def telnyx_webhook(request: dict):
    event_type = request.get("event_type")
    call_id = request.get("data", {}).get("id")

    if event_type == "call.initiated":
        requests.post(
            f"https://api.telnyx.com/v2/calls/{call_id}/actions/answer",
            headers={"Authorization": f"Bearer {TELNYX_API_KEY}"}
        )

    elif event_type == "call.answered":
        requests.post(
            f"https://api.telnyx.com/v2/calls/{call_id}/actions/start_audio_stream",
            headers={
                "Authorization": f"Bearer {TELNYX_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "stream_url": f"wss://{os.environ.get('HOSTNAME', 'tu_dominio')}/ws/{call_id}",
                "audio_format": "linear16"
            }
        )
        # Saludo inicial
        await send_tts_to_telnyx(call_id, "Hola, soy InglesPower. Puedes hablar y te responderé en inglés mientras hablas.")

    elif event_type == "call.hangup":
        if call_id in active_calls:
            ws = active_calls[call_id]
            await ws.close()
            del active_calls[call_id]
        print(f"Llamada {call_id} finalizada")

    return {"status": "ok"}

# -----------------------------
# WebSocket streaming en tiempo real
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
            audio_buffer.extend(data)

            # Fragmentos pequeños para ultra fluidez
            if len(audio_buffer) > 16000 * 0.3 * 2:  # 0.3s audio
                tmp_audio = audio_buffer
                audio_buffer = bytearray()
                asyncio.create_task(process_audio_real_time(tmp_audio, call_id))

    except WebSocketDisconnect:
        print(f"WebSocket cerrado para llamada {call_id}")
        if call_id in active_calls:
            del active_calls[call_id]

# -----------------------------
# Procesar audio y responder en streaming
# -----------------------------
async def process_audio_real_time(audio_bytes: bytes, call_id: str):
    transcript = await speech_to_text(audio_bytes)
    if transcript:
        # OpenAI streaming: cada palabra que genera GPT se envía inmediatamente a TTS
        async for chunk in openai_client.chat.completions.stream(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Eres un asistente que enseña inglés de forma rápida, clara y didáctica."},
                {"role": "user", "content": transcript}
            ]
        ):
            if chunk.choices[0].delta.get("content"):
                partial_text = chunk.choices[0].delta.content
                await send_tts_to_telnyx(call_id, partial_text)

# -----------------------------
# Convertir audio a texto
# -----------------------------
async def speech_to_text(audio_bytes: bytes):
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
# Convertir texto a TTS y enviar a Telnyx
# -----------------------------
async def send_tts_to_telnyx(call_id: str, text: str):
    if not text.strip():
        return
    tts_url = "https://api.elevenlabs.io/v1/text-to-speech/EXAVITQu4vr4xnSDxMaL/stream"
    headers = {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}
    body = {"text": text, "voice_settings": {"stability":0.7,"similarity_boost":0.8}}
    resp = requests.post(tts_url, headers=headers, json=body)

    play_url = f"https://api.telnyx.com/v2/calls/{call_id}/actions/play_audio"
    files = {"file": ("response.mp3", resp.content, "audio/mpeg")}
    play_headers = {"Authorization": f"Bearer {TELNYX_API_KEY}"}
    requests.post(play_url, headers=play_headers, files=files)
