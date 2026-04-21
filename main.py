import os
import asyncio
import uuid
import requests
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request

from config import Config
from ai import speech_to_text, ask_ai, text_to_speech
from supabase_client import obtener_minutos, restar_minuto

app = FastAPI()

# call_id → estado
calls = {}

# -------------------------
# ROOT
# -------------------------
@app.get("/")
async def root():
    return {"status": "AI call server running"}

# -------------------------
# WEBHOOK TELNYX
# -------------------------
@app.post("/webhook")
async def webhook(request: Request):

    body = await request.json()
    event = body.get("event_type")
    data = body.get("data", {})
    call_id = data.get("id")
    phone = data.get("from", {}).get("phone_number", "unknown")

    print("EVENT:", event)

    # ---------------------
    # LLAMADA ENTRANTE
    # ---------------------
    if event == "call.initiated":

        requests.post(
            f"https://api.telnyx.com/v2/calls/{call_id}/actions/answer",
            headers={"Authorization": f"Bearer {Config.TELNYX_API_KEY}"}
        )

    # ---------------------
    # LLAMADA CONTESTADA
    # ---------------------
    elif event == "call.answered":

        await speak(call_id, "Hola, soy tu tutor de inglés. Habla conmigo cuando quieras.")

        requests.post(
            f"https://api.telnyx.com/v2/calls/{call_id}/actions/start_audio_stream",
            headers={"Authorization": f"Bearer {Config.TELNYX_API_KEY}"},
            json={
                "stream_url": f"wss://{Config.DOMAIN}/ws/{call_id}",
                "audio_format": "linear16"
            }
        )

    # ---------------------
    # HANGUP
    # ---------------------
    elif event == "call.hangup":
        calls.pop(call_id, None)

    return {"ok": True}


# -------------------------
# WEBSOCKET AUDIO STREAM
# -------------------------
@app.websocket("/ws/{call_id}")
async def ws_audio(websocket: WebSocket, call_id: str):

    await websocket.accept()

    calls[call_id] = {
        "buffer": bytearray(),
        "processing": False
    }

    try:
        while True:
            data = await websocket.receive_bytes()

            call = calls.get(call_id)
            if not call:
                continue

            call["buffer"].extend(data)

            # procesar cada ~1 segundo
            if len(call["buffer"]) > 32000 and not call["processing"]:

                audio = call["buffer"]
                call["buffer"] = bytearray()

                asyncio.create_task(handle_audio(call_id, audio))

    except WebSocketDisconnect:
        calls.pop(call_id, None)


# -------------------------
# PROCESAR AUDIO
# -------------------------
async def handle_audio(call_id, audio):

    call = calls.get(call_id)
    if not call:
        return

    call["processing"] = True

    try:
        text = await speech_to_text(audio)

        if not text:
            return

        print("USER:", text)

        # ⚠️ aquí deberías mapear phone real por call_id
        phone = "user"

        # CONTROL DE MINUTOS
        if obtener_minutos(phone) <= 0:
            await speak(call_id, "No tienes minutos disponibles.")
            return

        restar_minuto(phone)

        response = await ask_ai(text)
        print("AI:", response)

        await speak(call_id, response)

    except Exception as e:
        print("ERROR:", e)

    call["processing"] = False


# -------------------------
# PLAY AUDIO EN LLAMADA
# -------------------------
async def speak(call_id, text):

    audio = await text_to_speech(text)

    requests.post(
        f"https://api.telnyx.com/v2/calls/{call_id}/actions/play_audio",
        headers={"Authorization": f"Bearer {Config.TELNYX_API_KEY}"},
        files={
            "file": ("audio.mp3", audio, "audio/mpeg")
        }
    )
