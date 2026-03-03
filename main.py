import os
import json
import base64
import asyncio
import time
from fastapi import FastAPI, Request, Response, WebSocket
import telnyx
from config import Config
from elevenlabs.client import ElevenLabs

app = FastAPI()

# 1. Clientes
el_client = ElevenLabs(api_key=Config.ELEVENLABS_API_KEY)
telnyx_client = telnyx.Telnyx(api_key=Config.TELNYX_API_KEY)
VOICE_ID = "WOY6pnQ1WCg0mrOZ54lM"
MI_URL_WSS = "wss://://inglespower.onrender.com"

@app.post("/webhook")
async def webhook(request: Request):
    try:
        # Evitamos el error de JSON vacío de tus logs
        body = await request.body()
        if not body: return Response(status_code=200)
            
        data = json.loads(body)
        payload = data.get("data", {}).get("payload", {})
        event_type = data.get("data", {}).get("event_type")
        call_id = payload.get("call_control_id")

        if event_type == "call.initiated" and call_id:
            # Contestamos la llamada
            telnyx_client.calls.call_control.answer(call_id)
            
            # ACTIVAMOS EL STREAMING
            telnyx_client.calls.call_control.streaming_start(
                call_id,
                stream_url=MI_URL_WSS,
                stream_track="inbound_track",
                stream_bidirectional_mode="rtp"
            )
            print(f"[OK] Stream solicitado para: {call_id}")

    except Exception as e:
        print(f"[ERROR WEBHOOK] {e}")
    return Response(status_code=200)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("[WS] ¡Thorthugo conectado al flujo de audio!")

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            # --- AQUÍ ES DONDE HABLA PRIMERO ---
            if msg["event"] == "start":
                print("[WS] Canal activo. Thorthugo saludando...")
                # Saludo inicial instantáneo
                await thorthugo_habla_stream(websocket, "Hi! I am Thorthugo, your AI English tutor. How can I help you today?")

            elif msg["event"] == "media":
                # Aquí llegará el audio de tu voz (Base64)
                # Para que te entienda, aquí deberíamos enviar 'msg["media"]["payload"]' 
                # a un servicio como Deepgram o Google Speech-to-Text.
                pass

    except Exception as e:
        print(f"[WS DISCONNECTED] {e}")

async def thorthugo_habla_stream(websocket, texto):
    """Envía audio de ElevenLabs en tiempo real al Websocket"""
    try:
        # ElevenLabs en modo STREAM (Latencia Cero)
        audio_stream = el_client.generate(
            text=texto,
            voice=VOICE_ID,
            model="eleven_multilingual_v2",
            stream=True
        )

        for chunk in audio_stream:
            if chunk:
                # Telnyx espera Base64
                encoded = base64.b64encode(chunk).decode("utf-8")
                await websocket.send_json({
                    "event": "media",
                    "media": {"payload": encoded}
                })
        print(f"[INFO] Thorthugo terminó su frase.")
    except Exception as e:
        print(f"[STREAM ERROR] {e}")
