import os
import json
import base64
import asyncio
from fastapi import FastAPI, Request, Response, WebSocket
import telnyx
from config import Config
from ai import generar_respuesta
from elevenlabs.client import ElevenLabs

app = FastAPI()

# Clientes e Identidad
el_client = ElevenLabs(api_key=Config.ELEVENLABS_API_KEY)
telnyx_client = telnyx.Telnyx(api_key=Config.TELNYX_API_KEY)
VOICE_ID = "WOY6pnQ1WCg0mrOZ54lM"
MI_URL_WSS = "wss://://inglespower.onrender.com" # Tu URL de Render

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    payload = data.get("data", {}).get("payload", {})
    event_type = data.get("data", {}).get("event_type")
    call_id = payload.get("call_control_id")

    if event_type == "call.initiated":
        # 1. Contestamos la llamada
        telnyx_client.calls.call_control.answer(call_id)
        
        # 2. Iniciamos el STREAMING (Manía de la v4)
        # Esto le dice a Telnyx: "Mándame el audio a mi Websocket"
        telnyx_client.calls.call_control.media_streaming_start(
            call_id,
            stream_url=MI_URL_WSS,
            stream_track="inbound_track"
        )
        print(f"[TELNYX] Streaming activado para {call_id}")

    return Response(status_code=200)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("[WS] Telnyx conectado al stream")

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            # Telnyx envía el evento 'start' cuando el stream está listo
            if msg["event"] == "start":
                print("[WS] Stream iniciado correctamente")
                # Thorthugo saluda en cuanto se abre el canal
                await thorthugo_habla(websocket, "Hello! I am Thorthugo. Ready to speak English?")

            # Aquí es donde Telnyx nos envía el audio del usuario
            elif msg["event"] == "media":
                # Nota: Para procesar lo que el usuario DICE, necesitarías 
                # un motor de transcripción (STT) en tiempo real aquí.
                pass

    except Exception as e:
        print(f"[WS ERROR] {e}")

async def thorthugo_habla(websocket, texto):
    """Genera audio en tiempo real y lo inyecta al stream de Telnyx"""
    try:
        # ElevenLabs en modo STREAM (Latencia mínima)
        audio_stream = el_client.generate(
            text=texto,
            voice=VOICE_ID,
            model="eleven_multilingual_v2",
            stream=True
        )

        for chunk in audio_stream:
            if chunk:
                # Telnyx espera el audio en Base64 dentro de un JSON 'media'
                encoded = base64.b64encode(chunk).decode("utf-8")
                await websocket.send_json({
                    "event": "media",
                    "media": {
                        "payload": encoded
                    }
                })
        print(f"[INFO] Thorthugo terminó de hablar")
    except Exception as e:
        print(f"[ERROR ELEVENLABS STREAM] {e}")
