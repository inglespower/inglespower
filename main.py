import telnyx
from telnyx import Telnyx  # Importamos el cliente moderno
from fastapi import FastAPI, Request, Response
from config import Config
from supabase_client import obtener_minutos, restar_minuto
from ai import generar_respuesta
# from telnyx_sms import enviar_sms # Asegúrate de corregir este archivo también

app = FastAPI()

# INICIALIZACIÓN MODERNA (V4)
client = Telnyx(api_key=Config.TELNYX_API_KEY)

@app.get("/")
async def health():
    return {"status": "online", "service": "InglesPower AI"}

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    event = data.get("data", {})
    payload = event.get("payload", {})
    call_id = payload.get("call_control_id")
    phone = payload.get("from")

    # 1. Al entrar la llamada: Validar minutos
    if event.get("event_type") == "call.initiated":
        minutos = obtener_minutos(phone)
        if minutos > 0:
            # CORRECCIÓN: client.calls en lugar de telnyx.Call
            client.calls.answer(call_control_id=call_id)
        else:
            # enviar_sms(phone, "Saldo insuficiente. Compra minutos en nuestra web.")
            client.calls.hangup(call_control_id=call_id)

    # 2. Cuando contesta: Saludo inicial
    elif event.get("event_type") == "call.answered":
        hablar(call_id, "Welcome to your English practice. How can I help you today?")

    # 3. Después de que la IA habla: Escuchar al usuario
    elif event.get("event_type") == "call.speak.ended":
        # CORRECCIÓN: client.calls
        client.calls.gather_using_ai(call_control_id=call_id, parameters={"language": "en-US"})

    # 4. Cuando el usuario termina de hablar: Procesar con IA
    elif event.get("event_type") == "call.gather.ended":
        transcripcion = payload.get("transcription")
        if transcripcion:
            respuesta = generar_respuesta(transcripcion)
            hablar(call_id, respuesta)
            restar_minuto(phone) 
        else:
            hablar(call_id, "I didn't catch that. Can you repeat?")

    return Response(status_code=200)

def hablar(call_id, texto):
    # CORRECCIÓN: client.calls
    client.calls.speak(
        call_control_id=call_id,
        payload=texto,
        voice="female",
        language="en-US"
    )
