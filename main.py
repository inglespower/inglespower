import os
import time
import requests
from fastapi import FastAPI, Request

app = FastAPI()

TELNYX_API_KEY = os.getenv("TELNYX_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVEN_API_KEY = os.getenv("ELEVENLABS_API_KEY")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

VOICE_ID = "21m00Tcm4TlvDq8ikWAM"


# -------------------------
# TELNYX API
# -------------------------

def telnyx_api(endpoint, payload):

    url = f"https://api.telnyx.com/v2/{endpoint}"

    headers = {
        "Authorization": f"Bearer {TELNYX_API_KEY}",
        "Content-Type": "application/json"
    }

    r = requests.post(url, headers=headers, json=payload)

    print("[TELNYX API]", r.status_code, "->", endpoint)

    try:
        print(r.json())
    except:
        print(r.text)

    return r


def answer_call(call_control_id):

    telnyx_api(
        f"calls/{call_control_id}/actions/answer",
        {}
    )


def play_audio(call_control_id, audio_url):

    telnyx_api(
        f"calls/{call_control_id}/actions/playback_start",
        {"audio_url": audio_url}
    )


def start_recording(call_control_id):

    telnyx_api(
        f"calls/{call_control_id}/actions/record_start",
        {}
    )


# -------------------------
# ELEVENLABS
# -------------------------

def tts(text):

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"

    headers = {
        "xi-api-key": ELEVEN_API_KEY,
        "Content-Type": "application/json"
    }

    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2"
    }

    r = requests.post(url, headers=headers, json=data)

    filename = f"voice_{int(time.time())}.wav"

    with open(filename, "wb") as f:
        f.write(r.content)

    return filename


# -------------------------
# SUPABASE
# -------------------------

def upload_audio(file):

    bucket = "audios"

    url = f"{SUPABASE_URL}/storage/v1/object/{bucket}/{file}"

    headers = {
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "audio/wav"
    }

    with open(file, "rb") as f:

        r = requests.post(url, headers=headers, data=f)

    public = f"{SUPABASE_URL}/storage/v1/object/public/{bucket}/{file}"

    print("PUBLIC:", public)

    return public


# -------------------------
# OPENAI
# -------------------------

def ask_ai(text):

    url = "https://api.openai.com/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }

    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a helpful phone assistant"},
            {"role": "user", "content": text}
        ]
    }

    r = requests.post(url, headers=headers, json=data)

    return r.json()["choices"][0]["message"]["content"]


# -------------------------
# WEBHOOK
# -------------------------

@app.post("/webhook")
async def webhook(request: Request):

    data = await request.json()

    event = data["data"]["event_type"]
    payload = data["data"]["payload"]

    call_control_id = payload["call_control_id"]

    print("\nEVENT:", event)
    print("CALL:", call_control_id)

    # CALL START

    if event == "call.initiated":

        print("Contestando llamada")

        answer_call(call_control_id)

    # CALL ANSWERED

    if event == "call.answered":

        greeting = "Soy Inglés Power. ¿Qué te gustaría aprender hoy? Pregúntame lo que quieras."

        voice = tts(greeting)

        url = upload_audio(voice)

        play_audio(call_control_id, url)

        start_recording(call_control_id)

    return {"ok": True}


@app.get("/")
def root():
    return {"AI": "PHONE AGENT RUNNING"}
