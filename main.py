import os
import json
import base64
import asyncio
from fastapi import FastAPI, Request, Response, WebSocket
import telnyx
from config import Config
from elevenlabs.client import ElevenLabs

app = FastAPI()

# Clientes
el_client = ElevenLabs(api_key=Config.ELEVENLABS_API_KEY)
telnyx_client = telnyx.Telnyx(api_key=Config.TELNYX_API_KEY)
VOICE_ID = "WOY6pnQ1WCg0mrOZ54lM"
MI_URL_WSS = "wss://://inglespower.onrender.com"

@app.post("/webhook")
async def webhook(request: Request):
    try:
        # CORRECCIÓN: Leer el cuerpo como texto primero para evitar el JSONDecodeError
        body = await request.body()
        if not body:
            return Response(status_code=200)
            
        data = json.loads(body)
        payload = data.get("data", {}).get("payload", {})
        event_type = data.get("data", {}).get("event_type")
        call_id = payload.get("call_control_id")

        if event_type == "call.initiated" and call_id:
            # 1. Contestar
            telnyx_client.calls.call_control.answer(call_id)
            
            # 2. Iniciar Streaming (Abre el Websocket)
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

            if msg["event"] == "start":
                # Saludo inicial por el stream
                await thorthugo_habla(websocket, "Hi! I'm Thorthugo. Ready to practice?")

            elif msg["event"] == "media":
                # Aquí llega el audio base64 del usuario
                pass

    except Exception as e:
        print(f"[WS DISCONNECTED] {e}")

async def thorthugo_habla(websocket, texto):
    """Envía audio de ElevenLabs pedazo a pedazo al stream"""
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
        print(f"[STREAM ERROR] {e}")
