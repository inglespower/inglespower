import os
import json
import base64
import io
import requests
from fastapi import FastAPI, Request, Response, WebSocket
import telnyx # Importación base
from config import Config
from ai import generar_respuesta
from openai import OpenAI

app = FastAPI()

# Inicialización
telnyx.api_key = Config.TELNYX_API_KEY
openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)

# URL del WebSocket
MI_URL_WSS = f"wss://{Config.DOMAIN}/ws"

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        event_type = data.get("data", {}).get("event_type")
        payload = data.get("data", {}).get("payload", {})
        call_id = payload.get("call_control_id")

        if event_type == "call.initiated" and call_id:
            print(f"[TELNYX] Llamada recibida. Contestando...")
            # SINTAXIS V4: call_control.create_answer
            telnyx.CallControl.answer(call_id)

        elif event_type == "call.answered" and call_id:
            print(f"[TELNYX] Contestada. Iniciando Stream...")
            # SINTAXIS V4: call_control.create_streaming_start
            telnyx.CallControl.streaming_start(
                call_id,
                stream_url=MI_URL_WSS,
                stream_track="inbound_track",
                bidirectional_mode="rtp"
            )

    except Exception as e:
        # Si falla el anterior por la versión, intentamos la alternativa directa:
        try:
            if event_type == "call.initiated":
                telnyx.Call.answer(call_id)
            elif event_type == "call.answered":
                telnyx.Call.streaming_start(call_id, stream_url=MI_URL_WSS, bidirectional_mode="rtp")
        except:
            print(f"[ERROR WEBHOOK DEFINITIVO] {e}")
            
    return Response(status_code=200)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("[WS] ¡CONECTADO! Thorthugo está en línea.")
    
    audio_buffer = bytearray()
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            if msg["event"] == "start":
                await thorthugo_habla(websocket, "¡Hola! Soy Thorthugo. Por fin estamos conectados.")

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

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
