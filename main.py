import os
import json
import base64
import asyncio
import io
import time
from fastapi import FastAPI, Request, Response, WebSocket
import telnyx
from config import Config
from ai import generar_respuesta
from elevenlabs.client import ElevenLabs
from openai import OpenAI

app = FastAPI()

# --- CLIENTES (Sintaxis v4.0.0) ---
el_client = ElevenLabs(api_key=Config.ELEVENLABS_API_KEY)
# El cliente se instancia así en v4
telnyx_client = telnyx.Telnyx(api_key=Config.TELNYX_API_KEY)
openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)

VOICE_ID = "WOY6pnQ1WCg0mrOZ54lM"
MI_URL_WSS = "wss://://inglespower.onrender.com"

@app.post("/webhook")
async def webhook(request: Request):
    try:
        body = await request.body()
        if not body: return Response(status_code=200)
            
        data = json.loads(body)
        payload = data.get("data", {}).get("payload", {})
        event_type = data.get("data", {}).get("event_type")
        call_id = payload.get("call_control_id")

        if event_type == "call.initiated" and call_id:
            # CORRECCIÓN V4: Se usa .calls directamente, sin .call_control
            telnyx_client.calls.answer(call_id)
            
            # Iniciamos el stream de audio
            telnyx_client.calls.streaming_start(
                call_id,
                stream_url=MI_URL_WSS,
                stream_track="inbound_track",
                stream_bidirectional_mode="rtp"
            )
            print(f"[OK] Streaming iniciado para {call_id}")

    except Exception as e:
        print(f"[ERROR WEBHOOK] {e}")

    return Response(status_code=200)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("[WS] ¡Canal de audio conectado!")
    
    audio_buffer = bytearray()

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            if msg["event"] == "start":
                # Thorthugo habla primero
                await thorthugo_habla(websocket, "Hi! I'm Thorthugo. I'm ready. Let's talk!")

            elif msg["event"] == "media":
                chunk = base64.b64decode(msg["media"]["payload"])
                audio_buffer.extend(chunk)

                # Procesar cada 2 segundos con Whisper
                if len(audio_buffer) > 32000:
                    audio_file = io.BytesIO(audio_buffer)
                    audio_file.name = "audio.wav"
                    
                    transcript = openai_client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file
                    )
                    
                    user_text = transcript.text
                    if user_text.strip():
                        print(f"[USER]: {user_text}")
                        ai_response = generar_respuesta(user_text)
                        await thorthugo_habla(websocket, ai_response)
                    
                    audio_buffer.clear()

    except Exception as e:
        print(f"[WS ERROR] {e}")

async def thorthugo_habla(websocket, texto):
    try:
        audio_stream = el_client.generate(
            text=texto,
            voice=VOICE_ID,
            model="eleven_multilingual_v2",
            stream=True
        )

        for chunk in audio_stream:
            if chunk:
                encoded = base64.b64encode(chunk).decode("utf-8")
                await websocket.send_json({
                    "event": "media",
                    "media": {"payload": encoded}
                })
    except Exception as e:
        print(f"[ERR ELEVENLABS] {e}")
