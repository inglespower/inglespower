import os
import json
import base64
import asyncio
import io
import requests
from fastapi import FastAPI, Request, Response, WebSocket
import telnyx
from config import Config
from ai import generar_respuesta
from openai import OpenAI

app = FastAPI()

# Configuración de Clientes
telnyx.api_key = Config.TELNYX_API_KEY
openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)

# URL del WebSocket (Limpia de protocolos duplicados)
MI_URL_WSS = f"wss://{Config.DOMAIN}/ws"

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        event_type = data.get("data", {}).get("event_type")
        payload = data.get("data", {}).get("payload", {})
        # ID de control de la llamada (Estándar Telnyx v2)
        call_id = payload.get("call_control_id")

        if event_type == "call.initiated":
            print(f"[TELNYX] Llamada entrante detectada. Contestando...")
            # COMANDO ACTUALIZADO: telnyx.CallControl
            telnyx.CallControl.answer(call_id)

        elif event_type == "call.answered":
            print(f"[TELNYX] Contestada. Conectando Stream a: {MI_URL_WSS}")
            # COMANDO ACTUALIZADO: telnyx.CallControl.streaming_start
            telnyx.CallControl.streaming_start(
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
    print("[WS] Conexión establecida con éxito.")
    
    audio_buffer = bytearray()

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            if msg["event"] == "start":
                print("[WS] Evento 'start' recibido. Thorthugo saludando...")
                await thorthugo_habla(websocket, "¡Hola! Soy Thorthugo. Ya estoy listo para hablar contigo.")

            elif msg["event"] == "media":
                # Recibimos audio del usuario
                chunk = base64.b64decode(msg["media"]["payload"])
                audio_buffer.extend(chunk)

                # Procesamos audio cada ~2 segundos (28000 bytes aprox)
                if len(audio_buffer) > 28000:
                    buffer_file = io.BytesIO(audio_buffer)
                    buffer_file.name = "audio.wav"
                    
                    transcript = openai_client.audio.transcriptions.create(
                        model="whisper-1", 
                        file=buffer_file
                    )
                    
                    if transcript.text.strip():
                        print(f"[USER]: {transcript.text}")
                        respuesta = generar_respuesta(transcript.text)
                        await thorthugo_habla(websocket, respuesta)
                    
                    audio_buffer.clear()

    except Exception as e:
        print(f"[WS DISCONNECTED] {e}")

async def thorthugo_habla(websocket, texto):
    """Genera audio mu-law 8000Hz (formato telefónico) y lo envía a Telnyx"""
    try:
        # El parámetro 'output_format=ulaw_8000' es CLAVE para que se escuche audio
        url = f"https://api.elevenlabs.io{Config.VOICE_ID}/stream?output_format=ulaw_8000"
        
        headers = {
            "xi-api-key": Config.ELEVENLABS_API_KEY,
            "Content-Type": "application/json"
        }
        
        payload = {
            "text": texto,
            "model_id": "eleven_multilingual_v2"
        }

        # Pedimos el audio a ElevenLabs con stream=True para rapidez
        with requests.post(url, json=payload, headers=headers, stream=True) as response:
            if response.status_code == 200:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        encoded = base64.b64encode(chunk).decode("utf-8")
                        # Enviamos el audio de vuelta al WebSocket de Telnyx
                        await websocket.send_json({
                            "event": "media",
                            "media": {"payload": encoded}
                        })
            else:
                print(f"[ERR ELEVENLABS] Status: {response.status_code}")

    except Exception as e:
        print(f"[ERR GENERANDO VOZ] {e}")

if __name__ == "__main__":
    import uvicorn
    # Render usa la variable PORT
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
