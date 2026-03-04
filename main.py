import os
import json
import base64
import io
import requests
from fastapi import FastAPI, Request, Response, WebSocket
from config import Config
from ai import generar_respuesta
from openai import OpenAI

app = FastAPI()

# Inicialización
openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)
# Limpiamos el dominio para el WebSocket
CLEAN_DOMAIN = Config.DOMAIN.replace("https://", "").replace("http://", "").strip("/")
MI_URL_WSS = f"wss://{CLEAN_DOMAIN}/ws"

# FUNCIÓN CORREGIDA: Sin el error de "comcalls"
def telnyx_command(endpoint, payload=None):
    # La barra "/" después de v2/ es la que arregla el error de tu imagen
    url = f"https://api.telnyx.com{endpoint.lstrip('/')}"
    headers = {
        "Authorization": f"Bearer {Config.TELNYX_API_KEY}",
        "Content-Type": "application/json"
    }
    try:
        if payload:
            res = requests.post(url, json=payload, headers=headers)
        else:
            res = requests.post(url, headers=headers)
        print(f"[TELNYX API] Status: {res.status_code} para {endpoint}")
        return res
    except Exception as e:
        print(f"[ERR TELNYX API] {e}")
        return None

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        payload = data.get("data", {}).get("payload", {})
        event_type = data.get("data", {}).get("event_type")
        call_id = payload.get("call_control_id")

        if event_type == "call.initiated" and call_id:
            print(f"[TELNYX] Contestando llamada: {call_id}")
            telnyx_command(f"calls/{call_id}/actions/answer")

        elif event_type == "call.answered" and call_id:
            print(f"[TELNYX] Iniciando Stream en: {MI_URL_WSS}")
            stream_payload = {
                "stream_url": MI_URL_WSS,
                "stream_track": "inbound_track",
                "bidirectional_mode": "rtp"
            }
            telnyx_command(f"calls/{call_id}/actions/streaming_start", stream_payload)

    except Exception as e:
        print(f"[ERROR WEBHOOK] {e}")
            
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
                print("[WS] Recibido evento START")
                await thorthugo_habla(websocket, "¡Hola! Soy Thorthugo. Por fin me escuchas fuerte y claro.")

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
        # Formato telefónico ulaw_8000 indispensable
        url = f"https://api.elevenlabs.io{Config.VOICE_ID}/stream?output_format=ulaw_8000"
        headers = {"xi-api-key": Config.ELEVENLABS_API_KEY, "Content-Type": "application/json"}
        payload = {"text": texto, "model_id": "eleven_multilingual_v2"}
        
        with requests.post(url, json=payload, headers=headers, stream=True) as response:
            if response.status_code == 200:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        encoded = base64.b64encode(chunk).decode("utf-8")
                        await websocket.send_json({
                            "event": "media",
                            "media": {"payload": encoded}
                        })
            else:
                print(f"[ERR EL] Status: {response.status_code}")
    except Exception as e:
        print(f"[ERR VOZ] {e}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
