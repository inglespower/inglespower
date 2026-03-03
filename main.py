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
from supabase_client import obtener_minutos, restar_minuto
from telnyx_sms import enviar_link_pago

app = FastAPI()

# 1. INSTANTIATE CLIENTS (The "Safe" Way)
# We create a specific client object to avoid "attribute" errors
telnyx_sdk = telnyx.Telnyx(api_key=Config.TELNYX_API_KEY)
el_client = ElevenLabs(api_key=Config.ELEVENLABS_API_KEY)
openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)

VOICE_ID = "WOY6pnQ1WCg0mrOZ54lM"
MI_URL_WSS = f"wss://{Config.DOMAIN}/ws"

@app.post("/webhook")
async def webhook(request: Request):
    try:
        body = await request.body()
        if not body: return Response(status_code=200)
        data = json.loads(body)
        
        event_type = data.get("data", {}).get("event_type")
        payload = data.get("data", {}).get("payload", {})
        call_id = payload.get("call_control_id")
        phone = payload.get("from")

        if event_type == "call.initiated" and call_id:
            print(f"[CALL] Incoming from: {phone}")
            minutos = obtener_minutos(phone)
            
            if minutos > 0:
                # USE THE SDK CLIENT (Works in all versions)
                telnyx_sdk.calls.answer(call_id)
                
                # START STREAMING
                telnyx_sdk.calls.streaming_start(
                    call_id,
                    stream_url=MI_URL_WSS,
                    stream_track="inbound_track",
                    stream_bidirectional_mode="rtp"
                )
                print(f"[OK] Stream started for {call_id}")
            else:
                telnyx_sdk.calls.hangup(call_id)
                enviar_link_pago(phone)

    except Exception as e:
        print(f"[ERR WEBHOOK] {e}")
    return Response(status_code=200)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("[WS] Thorthugo Connected!")
    
    audio_buffer = bytearray()

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            if msg["event"] == "start":
                await thorthugo_habla(websocket, "Hi! I am Thorthugo. I am finally working! Let's talk.")

            elif msg["event"] == "media":
                chunk = base64.b64decode(msg["media"]["payload"])
                audio_buffer.extend(chunk)

                if len(audio_buffer) > 32000:
                    buffer_file = io.BytesIO(audio_buffer)
                    buffer_file.name = "audio.wav"
                    transcript = openai_client.audio.transcriptions.create(model="whisper-1", file=buffer_file)
                    
                    if transcript.text.strip():
                        print(f"[USER]: {transcript.text}")
                        respuesta = generar_respuesta(transcript.text)
                        await thorthugo_habla(websocket, respuesta)
                    
                    audio_buffer.clear()

    except Exception as e:
        print(f"[WS DISCONNECTED] {e}")

async def thorthugo_habla(websocket, texto):
    try:
        audio_stream = el_client.generate(text=texto, voice=VOICE_ID, model="eleven_multilingual_v2", stream=True)
        for chunk in audio_stream:
            if chunk:
                encoded = base64.b64encode(chunk).decode("utf-8")
                await websocket.send_json({"event": "media", "media": {"payload": encoded}})
    except Exception as e:
        print(f"[ERR ELEVENLABS] {e}")
