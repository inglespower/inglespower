import os
import json
import base64
import io
import requests
from fastapi import FastAPI, Request, Response, WebSocket
from telnyx import Telnyx # <--- ESTA ES LA CLAVE
from config import Config
from ai import generar_respuesta
from openai import OpenAI

app = FastAPI()

# INICIALIZACIÓN DEL CLIENTE (Instancia física)
telnyx_client = Telnyx(api_key=Config.TELNYX_API_KEY)
openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)

MI_URL_WSS = f"wss://{Config.DOMAIN}/ws"

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        event_type = data.get("data", {}).get("event_type")
        payload = data.get("data", {}).get("payload", {})
        call_id = payload.get("call_control_id")

        if event_type == "call.initiated":
            print(f"[TELNYX] Contestando llamada...")
            # Método del cliente instanciado
            telnyx_client.calls.answer(call_id)

        elif event_type == "call.answered":
            print(f"[TELNYX] Iniciando Stream en: {MI_URL_WSS}")
            # Método del cliente instanciado
            telnyx_client.calls.streaming_start(
                call_id,
                stream_url=MI_URL_WSS,
                stream_track="inbound_track",
                bidirectional_mode="rtp"
            )
    except Exception as e:
        print(f"[ERROR WEBHOOK] {e}")
    return Response(status_code=200)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("[WS] ¡CONECTADO! Thorthugo está vivo.")
    
    audio_buffer = bytearray()
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg["event"] == "start":
                await thorthugo_habla(websocket, "¡Hola! Soy Thorthugo. Por fin me escuchas.")
            elif msg["event"] == "media":
                chunk = base64.b64decode(msg["media"]["payload"])
                audio_buffer.extend(chunk)
                if len(audio_buffer) > 28000:
                    buffer_file = io.BytesIO(audio_buffer)
                    buffer_file.name = "audio.wav"
                    transcript = openai_client.audio.transcriptions.create(model="whisper-1", file=buffer_file)
                    if transcript.text.strip():
                        print(f"[USER]: {transcript.text}")
                        respuesta = generar_respuesta(transcript.text)
                        await thorthugo_habla(websocket, respuesta)
                    audio_buffer.clear()
    except Exception as e:
        print(f"[WS DISCONNECT] {e}")

async def thorthugo_habla(websocket, texto):
    try:
        url = f"https://api.elevenlabs.io{Config.VOICE_ID}/stream?output_format=ulaw_8000"
        headers = {"xi-api-key": Config.ELEVENLABS_API_KEY, "Content-Type": "application/json"}
        payload = {"text": texto, "model_id": "eleven_multilingual_v2"}
        with requests.post(url, json=payload, headers=headers, stream=True) as response:
            if response.status_code == 200:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        encoded = base64.b64encode(chunk).decode("utf-8")
                        await websocket.send_json({"event": "media", "media": {"payload": encoded}})
    except Exception as e:
        print(f"[ERR VOZ] {e}")
