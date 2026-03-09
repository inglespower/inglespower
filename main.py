import os
import time
from fastapi import FastAPI, Request
from openai import OpenAI
import requests

app = FastAPI()

# -------------------------
# CONFIGURACIÓN
# -------------------------
TELNYX_API_KEY = os.getenv("TELNYX_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# -------------------------
# TELNYX API HELPER
# -------------------------
def telnyx_command(path, data):
    url = f"https://api.telnyx.com{path}"
    headers = {
        "Authorization": f"Bearer {TELNYX_API_KEY}",
        "Content-Type": "application/json"
    }
    response = requests.post(url, headers=headers, json=data)
    print(f"[TELNYX] {path} - Status: {response.status_code}")
    return response

# -------------------------
# LÓGICA DE INTELIGENCIA ARTIFICIAL
# -------------------------
def obtener_respuesta_openai(texto_usuario):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Eres InglesPower, un tutor de inglés amable. Responde de forma breve y clara."},
                {"role": "user", "content": texto_usuario}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error OpenAI: {e}")
        return "Lo siento, tuve un problema al procesar tu solicitud."

# -------------------------
# WEBHOOK PRINCIPAL
# -------------------------
@app.post("/webhook")
async def webhook(req: Request):
    data = await req.json()
    
    # Extraer datos básicos del evento
    event_type = data["data"]["event_type"]
    payload = data["data"]["payload"]
    call_control_id = payload.get("call_control_id")
    
    print(f"--- EVENTO RECIBIDO: {event_type} ---")

    # 1. CONTESTAR LA LLAMADA
    if event_type == "call.initiated":
        telnyx_command(f"calls/{call_control_id}/actions/answer", {})

    # 2. SALUDO INICIAL Y EMPEZAR A ESCUCHAR
    elif event_type == "call.answered":
        # Usamos 'gather_using_speak' para saludar y activar la escucha de inmediato
        telnyx_command(f"calls/{call_control_id}/actions/gather_using_speak", {
            "payload": "Hola, bienvenido a InglesPower. ¿En qué puedo ayudarte hoy?",
            "voice": "female",
            "language": "es-ES",
            "input_type": "speech" # Importante para que escuche voz
        })

    # 3. PROCESAR LO QUE EL USUARIO DIJO
    elif event_type == "call.gather.ended":
        # Este evento trae la transcripción automática de Telnyx
        texto_usuario = payload.get("transcription")
        
        if texto_usuario:
            print(f"Usuario dijo: {texto_usuario}")
            
            # Generar respuesta con OpenAI
            respuesta_ai = obtener_respuesta_openai(texto_usuario)
            print(f"IA responde: {respuesta_ai}")
            
            # Responder al usuario y volver a escuchar (bucle de conversación)
            telnyx_command(f"calls/{call_control_id}/actions/gather_using_speak", {
                "payload": respuesta_ai,
                "voice": "female",
                "language": "es-ES",
                "input_type": "speech"
            })
        else:
            # Si no entendió nada, vuelve a preguntar
            telnyx_command(f"calls/{call_control_id}/actions/gather_using_speak", {
                "payload": "No pude escucharte bien, ¿podrías repetirlo?",
                "voice": "female",
                "language": "es-ES",
                "input_type": "speech"
            })

    elif event_type == "call.hangup":
        print("Llamada finalizada por el usuario.")

    return {"status": "success"}

@app.get("/")
def health_check():
    return {"status": "online", "bot": "InglesPower"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
