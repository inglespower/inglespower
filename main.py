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

app = FastAPI()

# 1. Configuración de Clientes (Sintaxis v4 Telnyx y v2 ElevenLabs)
el_client = ElevenLabs(api_key=Config.ELEVENLABS_API_KEY)
telnyx_client = telnyx.Telnyx(api_key=Config.TELNYX_API_KEY)
openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)

VOICE_ID = "WOY6pnQ1WCg0mrOZ54lM"
MI_URL_WSS = "wss://://inglespower.onrender.com"

@app.post("/webhook")
async def webhook(request: Request):
    try:
        # Evitar el JSONDecodeError que se ve en tus logs
        body = await request.body()
        if not body: return Response(status_code=200)
        data = json.loads(body)
        
        event_type = data.get("data", {}).get("event_type")
        payload = data.get("data", {}).get("payload", {})
        call_id = payload.get("call_control_id")

        if event_type == "call.initiated" and call_id:
            # Contestamos la llamada
            telnyx_client.calls.call_control.answer(call_id)
            
            # INICIAMOS STREAMING RTP (La clave del Tiempo Real)
            telnyx_client.calls.call_control.streaming_start(
                call_id,
                stream_url=MI_URL_WSS,
                stream_track="inbound_track",
                stream_bidirectional_mode="rtp"
            )
            print(f"[TELNYX] Stream solicitado para {call_id}")

    except Exception as e:
        print(f"[ERR WEBHOOK] {e}")
    return Response(status_code=200)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("[WS] Conexión de audio en tiempo real establecida")
    
    # Buffer para acumular audio y transcribir con Whisper
    audio_buffer = bytearray()

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            if msg["event"] == "start":
                # Thorthugo habla primero al conectarse el audio
                await thorthugo_habla_stream(websocket, "Hi! I'm Thorthugo, your AI tutor. I'm listening. What's on your mind?")

            elif msg["event"] == "media":
                # Recibimos trozos de tu voz (Base64)
                chunk = base64.b64decode(msg["media"]["payload"])
                audio_buffer.extend(chunk)

                # Procesamos cada ~2 segundos de audio acumulado
                if len(audio_buffer) > 32000:
                    print("[WS] Transcribiendo con Whisper...")
                    
                    audio_file = io.BytesIO(audio_buffer)
                    audio_file.name = "audio.wav"
                    
                    # OpenAI Whisper escucha
                    transcript = openai_client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file
                    )
                    
                    user_text = transcript.text
                    if user_text.strip():
                        print(f"[USER]: {user_text}")
                        # La IA genera la respuesta
                        ai_response = generar_respuesta(user_text)
                        # Thorthugo responde por el stream instantáneamente
                        await thorthugo_habla_stream(websocket, ai_response)
                    
                    audio_buffer.clear()

    except Exception as e:
        print(f"[WS ERROR] {e}")

async def thorthugo_habla_stream(websocket, texto):
    """Genera audio con ElevenLabs y lo inyecta al stream sin esperas"""
    try:
        # Modo STREAM = Thorthugo empieza a hablar ANTES de terminar la frase
        audio_stream = el_client.generate(
            text=texto,
            voice=VOICE_ID,
            model="eleven_multilingual_v2",
            stream=True
        )

        for chunk in audio_stream:
            if chunk:
                # Codificamos y mandamos al WebSocket de Telnyx
                encoded = base64.b64encode(chunk).decode("utf-8")
                await websocket.send_json({
                    "event": "media",
                    "media": {"payload": encoded}
                })
        print(f"[OK] Frase terminada por Thorthugo.")
    except Exception as e:
        print(f"[ERR ELEVENLABS STREAM] {e}")
