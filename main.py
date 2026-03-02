import os
import uvicorn
import asyncio
from fastapi import FastAPI, Request, Response
from telnyx import Telnyx
from config import Config
from supabase_client import obtener_minutos, restar_minuto

app = FastAPI()

# Cliente Telnyx 4.x
telnyx_client = Telnyx(api_key=Config.TELNYX_KEY)


@app.get("/")
@app.head("/")
async def health():
    return {"status": "online"}


@app.post("/webhook")
async def handle_webhook(request: Request):
    try:
        data = await request.json()

        payload = data.get("data", {}).get("payload", {})
        event_type = data.get("data", {}).get("event_type")
        call_id = payload.get("call_control_id")
        from_number = payload.get("from")

        if not call_id:
            return Response(status_code=200)

        # 🔥 SOLO actuamos cuando la llamada ya fue contestada
        if event_type == "call.answered":

            balance = obtener_minutos(from_number)

            if balance > 0:

                telnyx_client.calls.actions.speak(
                    call_control_id=call_id,
                    payload="Hello! I am your AI English tutor. How can I help you today?",
                    voice="female",
                    language="en-US"
                )

                asyncio.create_task(cronometro_cobro(from_number, call_id))

            else:

                telnyx_client.calls.actions.speak(
                    call_control_id=call_id,
                    payload="No tienes minutos. Por favor recarga.",
                    voice="female",
                    language="es-ES"
                )

                await asyncio.sleep(4)

                telnyx_client.calls.actions.hangup(
                    call_control_id=call_id
                )

        # Si la llamada terminó, no hacemos nada
        if event_type == "call.hangup":
            print(f"Llamada terminada: {call_id}")

    except Exception as e:
        print(f"Error procesando lógica de llamada: {e}")

    return Response(status_code=200)


async def cronometro_cobro(phone, call_id):
    while True:
        await asyncio.sleep(60)

        restar_minuto(phone)

        if obtener_minutos(phone) <= 0:

            try:
                telnyx_client.calls.actions.speak(
                    call_control_id=call_id,
                    payload="Your time is up. Goodbye!",
                    voice="female",
                    language="en-US"
                )

                await asyncio.sleep(3)

                telnyx_client.calls.actions.hangup(
                    call_control_id=call_id
                )
            except:
                pass

            break


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
