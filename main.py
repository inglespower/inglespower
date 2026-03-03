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

# --- CLIENTES INSTANCIADOS ---
el_client = ElevenLabs(api_key=Config.ELEVENLABS_API_KEY)
telnyx_client = telnyx.Telnyx(api_key=Config.TELNYX_API_KEY)
openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)

VOICE_ID = "WOY6pnQ1WCg0mrOZ54lM"
MI_URL_WSS = "wss://://inglespower.onrender.com"

@app.post("/webhook")
async def webhook(request: Request):
    try:
        # PROTECCIÓN: Leer el cuerpo como texto para evitar el error de tu imagen
        body = await request.body()
        if not body:
            return Response(status_code=200)
            
        data = json.loads(body)
        payload = data.get("data", {}).get("payload", {})
        event_type = data.get("data", {}).get("event_type")
        call_id = payload.get("call_control_id")

        if event_type == "call.initiated" and call_id:
            # 1. Contestar la llamada (Sintaxis v4)
            telnyx_client.calls.call_control.answer(call_id)
            
            # 2. INICIAR STREAMING (Abre el canal de audio instantáneo)
            telnyx_client.calls.call_control.streaming_start(
                call_id,
                stream_url=MI_URL_WSS,
                stream_track="inbound_track",
                stream_bidirectional_mode="rtp"
            )
            print(f"[OK] Stream solicitado para ID: {call_id}")

    except Exception as e:
        print(f"[ERROR WEBHOOK] {e}")

    return Response(status_code=200)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("[WS] ¡Canal de audio conectado con Thorthugo!")
    
    # Buffer para acumular voz del usuario
    audio_buffer = bytearray()

    try:
        while True:
            # Recibir datos de audio de Telnyx
            data = await websocket.receive_text()
            msg = json.loads(data)

            if msg["event"] == "start":
                print("[WS] Stream activo. Thorthugo saludando...")
                # Thorthugo habla primero al conectarse el audio
                await thorthugo_habla(websocket, "Hi! I'm Thorthugo. I'm ready to practice English. Tell me something!")

            elif msg["event"] == "media":
                # Recibimos audio del usuario (Base64)
                chunk = base64.b64decode(msg["media"]["payload"])
                audio_buffer.extend(chunk)

                # Si tenemos ~2 segundos de audio, OpenAI Whisper lo "escucha"
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
                        # La IA genera la respuesta
                        ai_response = generar_respuesta(user_text)
                        # Thorthugo responde por el stream sin esperar
                        await thorthugo_habla(websocket, ai_response)
                    
                    audio_buffer.clear()

    except Exception as e:
        print(f"[WS ERROR] {e}")

async def thorthugo_habla(websocket, texto):
    """Genera audio con ElevenLabs y lo inyecta al stream sin archivos intermedios"""
    try:
        # ElevenLabs Stream = Thorthugo habla MIENTRAS se genera la voz
        audio_stream = el_client.generate(
            text=texto,
            voice=VOICE_ID,
            model="eleven_multilingual_v2",
            stream=True
        )

        for chunk in audio_stream:
            if chunk:
                # Convertimos a Base64 y mandamos al WebSocket
                encoded = base64.b64encode(chunk).decode("utf-8")
                await websocket.send_json({
                    "event": "media",
                    "media": {"payload": encoded}
                })
        print(f"[OK] Thorthugo terminó de hablar.")
    except Exception as e:
        print(f"[ERR ELEVENLABS STREAM] {e}")
