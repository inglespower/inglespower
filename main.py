import os
import random
from fastapi import FastAPI, Request
from openai import OpenAI
import requests

app = FastAPI()

# -------------------------
# CONFIG
# -------------------------
TELNYX_API_KEY = os.getenv("TELNYX_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

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

    print("TELNYX:", path, r.status_code)

    if r.text:
        print(r.text)

    return r


# -------------------------
# RESPUESTA OPENAI
# -------------------------
def generar_respuesta(texto):

    try:

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Eres InglesPower, un tutor amable que ayuda a aprender inglés. Responde corto y claro."
                },
                {
                    "role": "user",
                    "content": texto
                }
            ]
        )

        respuesta = resp.choices[0].message.content

        print("IA:", respuesta)

        return respuesta

    except Exception as e:

        print("ERROR OPENAI:", e)

        return "Lo siento, hubo un problema. ¿Puedes repetir?"


# -------------------------
# PREGUNTAS SI NO HABLA
# -------------------------
def pregunta_silencio():

    preguntas = [

        "No escuché nada. ¿Puedes decirme tu nombre?",

        "¿Te gustaría practicar inglés conmigo?",

        "Puedes preguntarme cualquier cosa en inglés o español.",

        "Por ejemplo puedes decir. How are you?",

        "¿Quieres aprender palabras nuevas en inglés?",

        "Intenta decir algo en inglés y yo te ayudo.",

        "También puedo ayudarte con pronunciación."

    ]

    return random.choice(preguntas)


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

    if not call_id:
        return {"ok": False}

    # -------------------------
    # CALL INITIATED
    # -------------------------
    if event == "call.initiated":

        telnyx_api(
            f"calls/{call_id}/actions/answer",
            {}
        )

    # -------------------------
    # CALL ANSWERED
    # -------------------------
    elif event == "call.answered":

        saludo = "Hola soy InglesPower. Que quieres aprender hoy. Puedes preguntarme lo que quieras."

        telnyx_api(
            f"calls/{call_id}/actions/gather_using_speak",
            {
                "payload": saludo,
                "voice": "female",
                "language": "es-US",
                "input_type": "speech",
                "timeout_secs": 10,
                "speech_timeout_secs": 3,
                "max_speech_duration_secs": 30
            }
        )

    # -------------------------
    # USUARIO TERMINA DE HABLAR
    # -------------------------
    elif event == "call.gather.ended":

        texto_usuario = payload.get("transcription")

        print("USUARIO:", texto_usuario)

        if not texto_usuario:

            pregunta = pregunta_silencio()

            telnyx_api(
                f"calls/{call_id}/actions/gather_using_speak",
                {
                    "payload": pregunta,
                    "voice": "female",
                    "language": "es-US",
                    "input_type": "speech",
                    "timeout_secs": 10,
                    "speech_timeout_secs": 3,
                    "max_speech_duration_secs": 30
                }
            )

            return {"ok": True}

        respuesta = generar_respuesta(texto_usuario)

        telnyx_api(
            f"calls/{call_id}/actions/gather_using_speak",
            {
                "payload": respuesta,
                "voice": "female",
                "language": "es-US",
                "input_type": "speech",
                "timeout_secs": 10,
                "speech_timeout_secs": 3,
                "max_speech_duration_secs": 30
            }
        )

    # -------------------------
    # CALL HANGUP
    # -------------------------
    elif event == "call.hangup":

        print("Llamada terminada")

    return {"ok": True}


# -------------------------
# ROOT
# -------------------------
@app.get("/")
def root():

    return {
        "status": "running",
        "bot": "InglesPower"
    }
