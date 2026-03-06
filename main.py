import os
import requests
from fastapi import FastAPI, Request

app = FastAPI()

TELNYX_API_KEY = os.getenv("TELNYX_API_KEY")
ELEVEN_API_KEY = os.getenv("ELEVENLABS_API_KEY")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

VOICE_ID = "21m00Tcm4TlvDq8ikWAM"

# ---------------------------
# TELNYX API
# ---------------------------

def telnyx_answer(call_control_id):
    url = f"https://api.telnyx.com/v2/calls/{call_control_id}/actions/answer"

    headers = {
        "Authorization": f"Bearer {TELNYX_API_KEY}",
        "Content-Type": "application/json"
    }

    r = requests.post(url, headers=headers)
    print("[TELNYX ANSWER]", r.status_code, r.text)


def telnyx_play_audio(call_control_id, audio_url):
    url = f"https://api.telnyx.com/v2/calls/{call_control_id}/actions/playback_start"

    headers = {
        "Authorization": f"Bearer {TELNYX_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "audio_url": audio_url
    }

    r = requests.post(url, headers=headers, json=data)

    print("[TELNYX PLAY]", r.status_code)
    print(r.text)


# ---------------------------
# ELEVENLABS TTS
# ---------------------------

def generate_voice(text):

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

    filename = "voice.wav"

    with open(filename, "wb") as f:
        f.write(r.content)

    return filename


# ---------------------------
# SUPABASE UPLOAD
# ---------------------------

def upload_audio(file_path):

    bucket = "audios"

    url = f"{SUPABASE_URL}/storage/v1/object/{bucket}/{file_path}"

    headers = {
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "audio/wav"
    }

    with open(file_path, "rb") as f:
        r = requests.post(url, headers=headers, data=f)

    public = f"{SUPABASE_URL}/storage/v1/object/public/{bucket}/{file_path}"

    print("PUBLIC URL:", public)

    return public


# ---------------------------
# WEBHOOK
# ---------------------------

@app.post("/webhook")
async def webhook(request: Request):

    data = await request.json()

    event = data["data"]["event_type"]

    payload = data["data"]["payload"]

    call_control_id = payload["call_control_id"]

    print("EVENT:", event)
    print("CALL:", call_control_id)

    # --------------------------------
    # CALL START
    # --------------------------------

    if event == "call.initiated":

        print("[TELNYX] Contestando llamada")

        telnyx_answer(call_control_id)

    # --------------------------------
    # CALL ANSWERED
    # --------------------------------

    if event == "call.answered":

        print("[TELNYX] Generando voz")

        file = generate_voice(
            "Hola. Gracias por llamar. Este es mi asistente de inteligencia artificial."
        )

        url = upload_audio(file)

        print("[TELNYX] Reproduciendo audio")

        telnyx_play_audio(call_control_id, url)

    return {"ok": True}


# ---------------------------
# ROOT
# ---------------------------

@app.get("/")
def root():
    return {"server": "running"}
