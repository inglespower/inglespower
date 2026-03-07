import os
import asyncio
from fastapi import FastAPI, WebSocket, Request
import requests
import websockets

app = FastAPI()

# -------------------------
# VARIABLES DE ENTORNO
# -------------------------
TELNYX_API_KEY = os.getenv("TELNYX_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# -------------------------
# TELNYX API
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
# WEBHOOK TELNYX
# -------------------------
@app.post("/webhook")
async def webhook(req: Request):
    data = await req.json()
    event = data["data"]["event_type"]
    payload = data["data"]["payload"]
    call_id = payload["call_control_id"]

    print("EVENT:", event)

    # Contestar llamada automáticamente
    if event == "call.initiated":
        telnyx_api(f"calls/{call_id}/actions/answer", {})

    # Cuando la llamada es contestada
    if event == "call.answered":
        # Esperar 1 segundo antes de iniciar streaming
        await asyncio.sleep(1)

        # Iniciar streaming bidireccional
        telnyx_api(
            f"calls/{call_id}/actions/streaming_start",
            {"stream_url": "wss://inglespower.onrender.com/ws"}
        )

        # Saludo inicial instantáneo
        saludo = (
            "Hola, soy InglesPower. "
            "¿Qué quieres aprender hoy? Puedes preguntarme lo que quieras."
        )

        # Playback inicial del saludo
        telnyx_api(
            f"calls/{call_id}/actions/playback_start",
            {"audio_url": f"https://api.elevenlabs.io/v1/text-to-speech-demo?text={saludo}"}
        )

    if event == "call.hangup":
        print("Llamada terminada")

    return {"ok": True}

# -------------------------
# WEBSOCKET TELNYX <-> OPENAI REALTIME
# -------------------------
@app.websocket("/ws")
async def ws_telnyx(ws: WebSocket):
    await ws.accept()
    print("Telnyx streaming conectado")

    # Conexión con OpenAI Realtime Voice
    async with websockets.connect(
        "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview",
        extra_headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "OpenAI-Beta": "realtime=v1"
        }
    ) as openai_ws:

        print("OpenAI Realtime conectado")

        # Función para enviar audio de Telnyx a OpenAI
        async def from_telnyx():
            while True:
                msg = await ws.receive_bytes()
                await openai_ws.send(msg)

        # Función para enviar audio de OpenAI de vuelta a Telnyx
        async def from_openai():
            while True:
                msg = await openai_ws.recv()
                await ws.send_bytes(msg)

        # Ejecutar ambas funciones simultáneamente
        await asyncio.gather(from_telnyx(), from_openai())

# -------------------------
# ROOT
# -------------------------
@app.get("/")
def root():
    return {"status": "running"}
