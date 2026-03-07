import os
import time
import json
import asyncio
import requests
from fastapi import FastAPI, Request, WebSocket
from supabase import create_client
from openai import OpenAI
from io import BytesIO

app = FastAPI()

# -------------------------
# CONFIGURACIÓN
# -------------------------
TELNYX_API_KEY = os.getenv("TELNYX_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
client = OpenAI(api_key=OPENAI_API_KEY)

# -------------------------
# FUNCIONES TELNYX
# -------------------------
def telnyx_api(path, data):
    url = f"https://api.telnyx.com/v2/{path}"
    headers = {
        "Authorization": f"Bearer {TELNYX_API_KEY}",
        "Content-Type": "application/json"
    }
    r = requests.post(url, headers=headers, json=data)
    print("[TELNYX]", r.status_code, path)
    if r.text:
        print(r.text)
    return r

# -------------------------
# FUNCIONES OPENAI TTS
# -------------------------
def generar_audio_bytes(texto):
    """
    Genera audio TTS con OpenAI y devuelve bytes listos para subir
    """
    response = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="alloy",
        input=texto
    )
    audio_bytes = BytesIO(response).read()
    return audio_bytes

# -------------------------
# FUNCIONES SUPABASE
# -------------------------
def subir_audio(bytes_audio, nombre_archivo):
    """
    Sube audio a Supabase y devuelve URL pública
    """
    path = f"audios/{nombre_archivo}"
    supabase.storage.from_("audios").upload(
        path,
        bytes_audio,
        {"content-type": "audio/mpeg"}
    )
    url = supabase.storage.from_("audios").get_public_url(path)
    print("URL PUBLICA:", url)
    return url

# -------------------------
# WEBHOOK TELNYX
# -------------------------
@app.post("/webhook")
async def webhook(req: Request):
    data = await req.json()
    event = data["data"]["event_type"]
    payload = data["data"]["payload"]
    call_id = payload["call_control_id"]

    print("EVENT:", event)

    if event == "call.initiated":
        telnyx_api(f"calls/{call_id}/actions/answer", {})

    if event == "call.answered":
        time.sleep(1)

        # Saludo inicial
        saludo = "Hola, soy InglesPower. ¿Qué quieres aprender hoy? Puedes preguntarme lo que quieras."
        audio_bytes = generar_audio_bytes(saludo)
        archivo_nombre = f"saludo_{int(time.time())}.mp3"
        url_audio = subir_audio(audio_bytes, archivo_nombre)

        telnyx_api(
            f"calls/{call_id}/actions/playback_start",
            {"audio_url": url_audio}
        )

        # Iniciar streaming Telnyx <-> OpenAI
        telnyx_api(
            f"calls/{call_id}/actions/streaming_start",
            {"stream_url": f"wss://inglespower.onrender.com/ws/{call_id}"}
        )

    if event == "call.hangup":
        print("Llamada terminada")

    return {"ok": True}

# -------------------------
# WEBSOCKET PARA STREAMING
# -------------------------
@app.websocket("/ws/{call_id}")
async def ws_telnyx(call_id: str, ws: WebSocket):
    await ws.accept()
    print(f"Streaming iniciado para call_id: {call_id}")

    # Conectar con OpenAI Realtime Voice
    import websockets
    async with websockets.connect(
        "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview",
        extra_headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "OpenAI-Beta": "realtime=v1"
        }
    ) as openai_ws:

        print("OpenAI Realtime conectado")

        # Instrucciones para voz natural y estilo tutor
        init_message = {
            "type": "session.update",
            "session": {
                "instructions": (
                    "Eres InglesPower, un asistente amistoso que enseña inglés. "
                    "Habla de manera clara, motivadora y natural. "
                    "Responde las preguntas del usuario de forma completa."
                )
            }
        }
        await openai_ws.send(json.dumps(init_message))

        async def from_telnyx():
            while True:
                try:
                    audio_bytes = await ws.receive_bytes()
                    await openai_ws.send(audio_bytes)  # enviar audio al modelo
                except Exception as e:
                    print("Error desde Telnyx:", e)
                    break

        async def from_openai():
            while True:
                try:
                    resp = await openai_ws.recv()
                    # Extraer audio generado
                    if isinstance(resp, bytes):
                        # Subir a Supabase y reproducir
                        archivo_nombre = f"respuesta_{int(time.time())}.mp3"
                        url_audio = subir_audio(resp, archivo_nombre)
                        telnyx_api(
                            f"calls/{call_id}/actions/playback_start",
                            {"audio_url": url_audio}
                        )
                except Exception as e:
                    print("Error desde OpenAI:", e)
                    break

        await asyncio.gather(from_telnyx(), from_openai())

# -------------------------
# ROOT
# -------------------------
@app.get("/")
def root():
    return {"status": "running"}
