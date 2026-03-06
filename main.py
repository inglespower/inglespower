import os
import requests
import time
from fastapi import FastAPI, Request
from supabase import create_client

app = FastAPI()

TELNYX_API_KEY = os.getenv("TELNYX_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

VOICE_ID = "21m00Tcm4TlvDq8ikWAM"

# -----------------------------
# TELNYX API
# -----------------------------

def telnyx_api(path, data):
url = f"https://api.telnyx.com/v2/{path}"

headers = {
"Authorization": f"Bearer {TELNYX_API_KEY}",
"Content-Type": "application/json"
}

r = requests.post(url, headers=headers, json=data)

print(f"[TELNYX API] {r.status_code} -> {path}")

if r.text:
print(r.text)

return r


# -----------------------------
# GENERAR AUDIO CON ELEVENLABS
# -----------------------------

def generar_audio(texto):

url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"

headers = {
"xi-api-key": ELEVENLABS_API_KEY,
"Content-Type": "application/json"
}

payload = {
"text": texto,
"model_id": "eleven_multilingual_v2"
}

r = requests.post(url, headers=headers, json=payload)

filename = f"tts_{int(time.time())}.wav"

with open(filename, "wb") as f:
f.write(r.content)

return filename


# -----------------------------
# SUBIR AUDIO A SUPABASE
# -----------------------------

def subir_audio(file):

path = f"audios/{file}"

with open(file, "rb") as f:
supabase.storage.from_("audios").upload(
path,
f,
{"content-type": "audio/wav"}
)

public = supabase.storage.from_("audios").get_public_url(path)

print("URL PUBLICA:", public)

return public


# -----------------------------
# WEBHOOK TELNYX
# -----------------------------

@app.post("/webhook")
async def webhook(req: Request):

body = await req.body()

if not body:
return {"ok": True}

data = await req.json()

event = data["data"]["event_type"]
call = data["data"]["payload"]["call_control_id"]

print("EVENT:", event)
print("CALL:", call)

# -------------------------
# LLAMADA ENTRANTE
# -------------------------

if event == "call.initiated":

print("[TELNYX] Contestando llamada")

telnyx_api(
f"calls/{call}/actions/answer",
{}
)

# -------------------------
# LLAMADA CONTESTADA
# -------------------------

if event == "call.answered":

print("[TELNYX] Generando voz...")

audio = generar_audio(
"Hola, soy tu asistente de inteligencia artificial. ¿En qué puedo ayudarte?"
)

url_audio = subir_audio(audio)

time.sleep(2)

print("[TELNYX] Reproduciendo audio")

telnyx_api(
f"calls/{call}/actions/playback_start",
{
"audio_url": url_audio
}
)

# -------------------------
# LLAMADA FINALIZADA
# -------------------------

if event == "call.hangup":

print("[TELNYX] Llamada terminada")

return {"ok": True}


# -----------------------------
# ROOT
# -----------------------------

@app.get("/")
def root():
return {"status": "running"}
