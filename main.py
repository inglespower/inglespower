import time
from telnyx import Telnyx
from fastapi import FastAPI, Request, Response
from config import Config
from supabase_client import obtener_minutos, restar_minuto
from ai import generar_respuesta

app = FastAPI()

# Inicialización obligatoria para v4
client = Telnyx(api_key=Config.TELNYX_API_KEY)

@app.get("/")
async def health():
    return {"status": "online", "service": "InglesPower AI"}

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        event = data.get("data", {})
        payload = event.get("payload", {})
        call_id = payload.get("call_control_id")
        phone = payload.get("from")
        event_type = event.get("event_type")

        # 1. LLAMADA INICIADA: Validar saldo y contestar
        if event_type == "call.initiated":
            minutos = obtener_minutos(phone)
            print(f"Llamada de {phone}. Minutos: {minutos}. Contestando...")
            if minutos > 0:
                # SINTAXIS CORRECTA V4: client.calls.actions.answer(id)
                client.calls.actions.answer(call_id)
            else:
                client.calls.actions.hangup(call_id)

        # 2. LLAMADA CONTESTADA: Saludo inicial
        elif event_type == "call.answered":
            time.sleep(1.5) 
            hablar(call_id, "Welcome to your English practice. How can I help you today?")

        # 3. FIN DE AUDIO DE IA: Activar escucha (Gather)
        elif event_type == "call.speak.ended":
            # SINTAXIS CORRECTA V4: client.calls.actions.gather_using_ai(id, ...)
            client.calls.actions.gather_using_ai(
                call_id, 
                parameters={"language": "en-US"}
            )

        # 4. USUARIO TERMINA DE HABLAR: Procesar respuesta
        elif event_type == "call.gather.ended":
            transcripcion = payload.get("transcription")
            if transcripcion:
                respuesta = generar_respuesta(transcripcion)
                hablar(call_id, respuesta)
                restar_minuto(phone)
            else:
                hablar(call_id, "I'm sorry, I didn't hear you. Could you repeat that?")

    except Exception as e:
        print(f"Error detectado en Webhook: {e}")

    return Response(status_code=200)

def hablar(call_id, texto):
    try:
        # SINTAXIS CORRECTA V4: client.calls.actions.speak(id, ...)
        client.calls.actions.speak(
            call_id,
            payload=texto,
            voice="female",
            language="en-US"
        )
    except Exception as e:
        print(f"Error al ejecutar speak: {e}")
