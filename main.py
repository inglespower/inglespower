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
# Importa tus otros módulos (asegúrate de que existan en tu repo)
try:
    from supabase_client import obtener_minutos, restar_minuto
    from telnyx_sms import enviar_link_pago
except ImportError:
    print("[WARN] Módulos de Supabase o SMS no encontrados, saltando lógica...")

app = FastAPI()

# Configuración de Clientes
telnyx.api_key = Config.TELNYX_API_KEY
openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)

# Limpiamos el dominio para evitar el error de doble protocolo (https://wss://)
CLEAN_DOMAIN = Config.DOMAIN.replace("https://", "").replace("http://", "").strip("/")
MI_URL_WSS = f"wss://{CLEAN_DOMAIN}/ws"

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        event_type = data.get("data", {}).get("event_type")
        payload = data.get("data", {}).get("payload", {})
        call_control_id = payload.get("call_control_id")
        phone = payload.get("from")

        if event_type == "call.initiated":
            print(f"[CALL] Entrante de: {phone}")
            # Validar minutos (Opcional, según tu lógica)
            # if obtener_minutos(phone) > 0:
            telnyx.Call.answer(call_control_id)
            # else:
            #     telnyx.Call.hangup(call_control_id)

        elif event_type == "call.answered":
            print(f"[STREAM] Iniciando WebSocket en: {MI_URL_WSS}")
            # Comando oficial Telnyx v2 para streaming
            telnyx.Call.streaming_start(
                call_control_id,
                stream_url=MI_URL_WSS,
                stream_track="inbound_track",
                bidirectional_mode="rtp"
            )

    except Exception as e:
        print(f"[ERR WEBHOOK] {e}")
    return Response(status_code=200)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("[WS] Thorthugo conectado y escuchando...")
    
    audio_buffer = bytearray()

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            if msg["event"] == "start":
                print("[WS] Stream iniciado por Telnyx")
                await thorthugo_habla(websocket, "¡Hola! Soy Thorthugo. Ya estoy funcionando, ¿en qué puedo ayudarte?")

            elif msg["event"] == "media":
                # Recibimos audio de Telnyx
                chunk = base64.b64decode(msg["media"]["payload"])
                audio_buffer.extend(chunk)

                # Procesamos audio cada ~2 segundos (ajustable)
                if len(audio_buffer) > 25000:
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
    """Genera audio en formato telefónico mu-law 8000Hz y lo envía al WS"""
    try:
        # IMPORTANTE: Pedimos 'ulaw_8000' para que el teléfono lo entienda
        url = f"https://api.elevenlabs.io{Config.VOICE_ID}/stream?output_format=ulaw_8000"
        
        headers = {
            "xi-api-key": Config.ELEVENLABS_API_KEY,
            "Content-Type": "application/json"
        }
        
        payload = {
            "text": texto,
            "model_id": "eleven_multilingual_v2"
        }

        # Streaming desde ElevenLabs para menor latencia
        with requests.post(url, json=payload, headers=headers, stream=True) as response:
            if response.status_code != 200:
                print(f"[ERR EL] Status: {response.status_code}")
                return

            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    encoded = base64.b64encode(chunk).decode("utf-8")
                    # Formato que Telnyx espera para reproducir audio
                    await websocket.send_json({
                        "event": "media",
                        "media": {"payload": encoded}
                    })
    except Exception as e:
        print(f"[ERR ELEVENLABS] {e}")

if __name__ == "__main__":
    import uvicorn
    # Render usa la variable de entorno PORT
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
