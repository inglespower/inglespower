from fastapi import FastAPI, Request, Response # Importamos Response
from twilio.twiml.voice_response import VoiceResponse, Gather
from supabase_client import get_minutes, subtract_minute, add_minutes
from twilio_client import send_sms
from ai import generate_reply

app = FastAPI()

@app.post("/voice")
async def voice(request: Request):
    form = await request.form()
    phone = form.get("From")
    resp = VoiceResponse()

    if get_minutes(phone) <= 0:
        resp.say("You have no minutes. Please recharge your account. Thank you.", voice="alice")
        # Cambio: Retornar con media_type XML
        return Response(content=str(resp), media_type="application/xml")

    gather = Gather(input="speech", action="/process", method="POST", speechTimeout="auto")
    gather.say("Hello. I am your bilingual English coach. You can ask me anything.", voice="alice")
    resp.append(gather)
    
    return Response(content=str(resp), media_type="application/xml")

@app.post("/process")
async def process(request: Request):
    form = await request.form()
    phone = form.get("From")
    speech = form.get("SpeechResult", "")
    resp = VoiceResponse()

    if get_minutes(phone) <= 0:
        resp.say("Your time is finished. Goodbye.", voice="alice")
        return Response(content=str(resp), media_type="application/xml")

    subtract_minute(phone)
    reply = generate_reply(speech)

    if get_minutes(phone) == 1:
        resp.say("You have one minute remaining.", voice="alice")

    gather = Gather(input="speech", action="/process", method="POST", speechTimeout="auto")
    gather.say(reply, voice="alice")
    resp.append(gather)
    
    return Response(content=str(resp), media_type="application/xml")

@app.post("/purchase")
async def purchase(request: Request):
    # Este se queda igual porque devuelve un JSON estándar
    data = await request.json()
    phone = data.get("phone")
    amount = float(data.get("amount", 0))

    minutes = {2: 5, 4: 10, 6: 15}.get(amount, 0)

    if minutes > 0:
        add_minutes(phone, minutes)
        send_sms(phone, f"Thank you. You now have {get_minutes(phone)} minutes.")

    return {"status": "ok"}
