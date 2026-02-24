from fastapi import FastAPI, Request
from twilio.twiml.voice_response import VoiceResponse, Gather
from supabase_client import get_minutes, subtract_minute, add_minutes
from twilio_client import send_sms
from ai import generate_reply

app = FastAPI()

# -------------------------
# VOICE ENDPOINT
# -------------------------
@app.post("/voice")
async def voice(request: Request):
    form = await request.form()
    phone = form.get("From")

    resp = VoiceResponse()

    # Verificar minutos
    if get_minutes(phone) <= 0:
                resp.say(
        "You have no minutes. Please recharge your account. Thank you.",
            voice="alice"
                )


    gather = Gather(
        input="speech",
        action="/process",
        method="POST",
        speechTimeout="auto"
)

    gather.say(
        "Hello. I am your bilingual English coach. You can ask me anything.",
        voice="alice"
)

    resp.append(gather)
    return str(resp)


# -------------------------
# PROCESAR CONVERSACIÓN
# -------------------------
@app.post("/process")
async def process(request: Request):
    form = await request.form()
    phone = form.get("From")
    speech = form.get("SpeechResult", "")

    resp = VoiceResponse()

    # verificar minutos
    if get_minutes(phone) <= 0:
            resp.say("Your time is finished. Goodbye.", voice="alice")
    return str(resp)

    # restar 1 minuto
    subtract_minute(phone)

# generar respuesta AI
reply = generate_reply(speech)

# aviso cuando queda 1 minuto
if get_minutes(phone) == 1:
        resp.say("You have one minute remaining.", voice="alice")

# responder
gather = Gather(
input="speech",
action="/process",
method="POST",
speechTimeout="auto"
)

gather.say(reply, voice="alice")

resp.append(gather)
    return str(resp)


# -------------------------
# COMPRA (ZELLE MANUAL)
# -------------------------
@app.post("/purchase")
async def purchase(request: Request):
    data = await request.json()

phone = data.get("phone")
amount = float(data.get("amount", 0))

minutes = 0
if amount == 2:
        minutes = 5
elif amount == 4:
    minutes = 10
elif amount == 6:
    minutes = 15

    if minutes > 0:
        add_minutes(phone, minutes)

        send_sms(
        phone,
        f"Thank you for your purchase. You now have {get_minutes(phone)} minutes in InglesPower."
        )

    return {"status": "ok"}
