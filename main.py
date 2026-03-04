import os
import json
import base64
import asyncio
import io
from fastapi import FastAPI, Request, Response, WebSocket
import telnyx
from config import Config
from ai import generar_respuesta
from elevenlabs.client import ElevenLabs
from openai import OpenAI
# Importa tus otros módulos aquí

app = FastAPI()

# Inicialización de Clientes
telnyx.api_key = Config.TELNYX_API_KEY
el_client = ElevenLabs(api_key=Config.ELEVENLABS_API_KEY)
openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)

VOICE_ID = "WOY6pnQ1WCg0mrOZ54lM"
MI_URL_WSS = f"wss://{Config.DOMAIN}/ws"

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        event_type = data.get("data", {}).get("event_type")
        payload = data.get("data", {}).get("payload", {})
        call_control_id = payload.get("call_control_id")
        
        # 1. Al recibir la llamada
        if event_type == "call.initiated":
            print(f"[CALL] Iniciada: {call_control_id}")
            # El comando correcto en v2 es call_control.answer
            telnyx.Call.answer(call_control_id)

        # 2. Cuando la llamada es contestada, iniciamos el stream
        elif event_type == "call.answered":
            print(f"[STREAM] Iniciando en: {call_control_id}")
            # Comando correcto para streaming bidireccional
            telnyx.Call.streaming_start(
                call_control_id,
                stream_url=MI_URL_WSS,
                stream_track="inbound_track",
                bidirectional_mode="rtp" # IMPORTANTE
            )

    except Exception as e:
        print(f"[ERR WEBHOOK] {e}")
    return Response(status_code=200)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("[WS] Conectado a Telnyx")
    
    audio_buffer = bytearray()
    stream_id = None

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            if msg["event"] == "start":
                stream_id = msg.get("stream_id")
                print(f"[WS] Stream ID: {stream_id}")
                await thorthugo_habla(websocket, "Hola, soy Thorthugo. ¿En qué puedo ayudarte?", stream_id)

            elif msg["event"] == "media":
                # Telnyx manda audio en base64
                chunk = base64.b64decode(msg["media"]["payload"])
                audio_buffer.extend(chunk)

                # Procesamos cada 2 segundos aprox de audio (depende del sample rate)
                if len(audio_buffer) > 20000: 
                    buffer_file = io.BytesIO(audio_buffer)
                    buffer_file.name = "audio.wav"
                    
                    transcript = openai_client.audio.transcriptions.create(
                        model="whisper-1", 
                        file=buffer_file
                    )
                    
                    if transcript.text.strip():
                        print(f"[USER]: {transcript.text}")
                        respuesta = generar_respuesta(transcript.text)
                        await thorthugo_habla(websocket, respuesta, stream_id)
                    
                    audio_buffer.clear()

    except Exception as e:
        print(f"[WS DISCONNECTED] {e}")

async def thorthugo_habla(websocket, texto, stream_id):
    try:
        # ElevenLabs genera el audio
        audio_stream = el_client.generate(
            text=texto, 
            voice=VOICE_ID, 
            model="eleven_multilingual_v2", 
            stream=True
        )
        
        for chunk in audio_stream:
            if chunk:
                encoded = base64.b64encode(chunk).decode("utf-8")
                # El formato de salida debe incluir el stream_id si Telnyx lo requiere
                await websocket.send_json({
                    "event": "media",
                    "media": {
                        "payload": encoded
                    }
                })
    except Exception as e:
        print(f"[ERR ELEVENLABS] {e}")
