import os
import time
import requests
from fastapi import FastAPI, Request
from supabase import create_client
from openai import OpenAI

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
# FUNCIONES OPENAI
# -------------------------
def generar_audio(texto):
    """Genera audio con OpenAI TTS y devuelve bytes"""
    response = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="alloy",
        input=texto
    )
    return response  # bytes del audio mp3

# -------------------------
# FUNCIONES SUPABASE
# -------------------------
def subir_audio(bytes_audio, nombre_archivo):
    """Sube audio a Supabase y devuelve URL pública"""
    path = f"audios/{nombre_archivo}"
    supabase.storage.from_("audios").upload(path, bytes_audio, {"content-type": "audio/mpeg"})
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

    # Contestar llamada automáticamente
    if event == "call.initiated":
        telnyx_api(f"calls/{call_id}/actions/answer", {})

    # Cuando la llamada es contestada
    if event == "call.answered":
        time.sleep(1)

        # Saludo inicial
        saludo = "Hola, soy InglesPower. ¿Qué quieres aprender hoy? Puedes preguntarme lo que quieras."
        audio_bytes = generar_audio(saludo)
        archivo_nombre = f"saludo_{int(time.time())}.mp3"
        url_audio = subir_audio(audio_bytes, archivo_nombre)

        # Reproducir audio en Telnyx
        telnyx_api(
            f"calls/{call_id}/actions/playback_start",
            {"audio_url": url_audio}
        )

    if event == "call.hangup":
        print("Llamada terminada")

    return {"ok": True}

# -------------------------
# ROOT
# -------------------------
@app.get("/")
def root():
    return {"status": "running"}
