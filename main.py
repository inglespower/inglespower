import requests
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request

from config import Config
from ai import speech_to_text, ask_ai, text_to_speech
from supabase_client import obtener_minutos, restar_minuto

app = FastAPI()

calls = {}

# -----------------------------
# ROOT (para ver si el server vive)
# -----------------------------
@app.get("/")
async def root():
    print("SERVER OK")
    return {"status": "ok"}

# -----------------------------
# WEBHOOK TELNYX
# -----------------------------
@app.post("/webhook")
async def webhook(request: Request):

    body = await request.json()

    print("🔥 WEBHOOK RECIBIDO:", body)

    event = body.get("event_type")
    data = body.get("data", {})

    call_id = data.get("id")

    if not call_id:
        print("❌ NO CALL ID")
        return {"ok": True}

    # -------------------------
    # LLAMADA ENTRANTE
    # -------------------------
    if event == "call.initiated":
        print("📞 CALL INITIATED")

        try:
            r = requests.post(
                f"https://api.telnyx.com/v2/calls/{call_id}/actions/answer",
                headers={"Authorization": f"Bearer {Config.TELNYX_API_KEY}"}
            )
            print("ANSWER RESPONSE:", r.status_code, r.text)
        except Exception as e:
            print("ERROR ANSWER:", e)

    # -------------------------
    # CALL ANSWERED
    # -------------------------
    elif event == "call.answered":
        print("📞 CALL ANSWERED")

        try:
            # 1. START STREAM PRIMERO (IMPORTANTE)
            r = requests.post(
                f"https://api.telnyx.com/v2/calls/{call_id}/actions/start_audio_stream",
                headers={"Authorization": f"Bearer {Config.TELNYX_API_KEY}"},
                json={
                    "stream_url": f"wss://{Config.DOMAIN}/ws/{call_id}",
                    "audio_format": "linear16"
                }
            )
            print("STREAM RESPONSE:", r.status_code, r.text)

        except Exception as e:
            print("ERROR STREAM:", e)

    return {"ok": True}

# -----------------------------
# WEBSOCKET AUDIO
# -----------------------------
@app.websocket("/ws/{call_id}")
async def ws(websocket: WebSocket, call_id: str):

    await websocket.accept()

    print("🟢 WS CONNECTED:", call_id)

    calls[call_id] = {
        "buffer": bytearray(),
        "processing": False
    }

    try:
        while True:

            data = await websocket.receive_bytes()

            print("🎧 AUDIO RECIBIDO:", len(data))

            call = calls.get(call_id)
            if not call:
                continue

            call["buffer"].extend(data)

            # procesar rápido
            if len(call["buffer"]) > 16000 and not call["processing"]:

                audio = call["buffer"]
                call["buffer"] = bytearray()

                asyncio.create_task(process(call_id, audio))

    except WebSocketDisconnect:
        print("🔴 WS DISCONNECTED")
        calls.pop(call_id, None)

# -----------------------------
# PROCESS AUDIO
# -----------------------------
async def process(call_id, audio):

    call = calls.get(call_id)
    if not call:
        return

    call["processing"] = True

    try:
        print("🧠 PROCESANDO AUDIO...")

        text = await speech_to_text(audio)

        print("🗣 USER:", text)

        if not text:
            return

        response = await ask_ai(text)

        print("🤖 AI:", response)

        await speak(call_id, response)

    except Exception as e:
        print("❌ ERROR PROCESS:", e)

    call["processing"] = False

# -----------------------------
# SPEAK
# -----------------------------
async def speak(call_id, text):

    try:
        audio = await text_to_speech(text)

        r = requests.post(
            f"https://api.telnyx.com/v2/calls/{call_id}/actions/play_audio",
            headers={"Authorization": f"Bearer {Config.TELNYX_API_KEY}"},
            files={
                "file": ("audio.mp3", audio, "audio/mpeg")
            }
        )

        print("🔊 PLAY RESPONSE:", r.status_code)

    except Exception as e:
        print("ERROR SPEAK:", e)
