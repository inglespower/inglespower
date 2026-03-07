import os
import json
import time
from fastapi import FastAPI, Request
from supabase import create_client
from openai import OpenAI
import requests
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
# GENERAR AUDIO OPENAI
# -------------------------
def generar_audio_bytes(texto):
    response = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="alloy",
        input=texto
    )
    return response.read()  # Devuelve bytes

# -------------------------
# SUBIR AUDIO A SUPABASE
# -------------------------
def subir_audio(bytes_audio, nombre_archivo):
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
# PROCESAR AUDIO DEL USUARIO
# -------------------------
def procesar_audio_usuario(audio_bytes):
    transcript = client.audio.transcriptions.create(
        file=BytesIO(audio_bytes),
        model="whisper-1"
    )
    texto_usuario = transcript.text
    print("Usuario dijo:", texto_usuario)
    return texto_usuario

def generar_respuesta(texto_usuario):
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": texto_usuario}]
    )
    respuesta = resp.choices[0].message["content"]
    print("Asistente responde:", respuesta)
    return respuesta

# -------------------------
# WEBHOOK TELNYX
# -------------------------
@app.post("/webhook")
async def webhook(req: Request):
    data = await req.json()
    event = data["data"]["event_type"]
    payload = data["data"]["payload"]
    call_id = payload.get("call_control_id")
    print("EVENT:", event)

    # CONTESTAR LLAMADA
    if event == "call.initiated":
        telnyx_api(f"calls/{call_id}/actions/answer", {})

    # SALUDO INICIAL
    if event == "call.answered":
        saludo = "Hola, soy InglesPower. ¿Qué quieres aprender hoy? Puedes preguntarme lo que quieras."
        audio_bytes = generar_audio_bytes(saludo)
        archivo_nombre = f"saludo_{int(time.time())}.mp3"
        url_audio = subir_audio(audio_bytes, archivo_nombre)
        telnyx_api(f"calls/{call_id}/actions/playback_start", {"audio_url": url_audio})

    # ESCUCHAR AUDIO DEL USUARIO
    if event == "input.audio.received":
        # Los bytes llegan en base64 en payload["audio_chunk"]
        import base64
        audio_bytes = base64.b64decode(payload["audio_chunk"])
        texto_usuario = procesar_audio_usuario(audio_bytes)
        respuesta = generar_respuesta(texto_usuario)
        audio_bytes_resp = generar_audio_bytes(respuesta)
        archivo_nombre = f"resp_{int(time.time())}.mp3"
        url_audio = subir_audio(audio_bytes_resp, archivo_nombre)
        telnyx_api(f"calls/{call_id}/actions/playback_start", {"audio_url": url_audio})

    if event == "call.hangup":
        print("Llamada terminada")

    return {"ok": True}

# -------------------------
# ROOT
# -------------------------
@app.get("/")
def root():
    return {"status": "running"}
