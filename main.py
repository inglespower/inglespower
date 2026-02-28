from fastapi import FastAPI, Request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather
from supabase_client import get_minutes, subtract_minute, add_minutes
from twilio_client import send_sms 
from ai import generate_reply

app = FastAPI()

@app.post("/voice")
async def voice(request: Request):
    form = await request.form()
    # Telnyx envía el número en 'From' o 'from', usamos .get para evitar errores
    phone = form.get("From") or form.get("from")
    resp = VoiceResponse()

    # Verificamos minutos en Supabase
    minutes = get_minutes(phone)
    if minutes <= 0:
        resp.say("You have no minutes. Please recharge your account at our website. Thank you.", voice="alice")
        return Response(content=str(resp), media_type="application/xml")

    # Gather para capturar la voz del usuario
    gather = Gather(input="speech", action="/process", method="POST", speechTimeout="auto", language="en-US")
    gather.say("Hello! I am your EnglishPower coach. How can I help you practice today?", voice="alice")
    resp.append(gather)
    
    return Response(content=str(resp), media_type="application/xml")

@app.post("/process")
async def process(request: Request):
    form = await request.form()
    phone = form.get("From") or form.get("from")
    speech = form.get("SpeechResult", "")
    resp = VoiceResponse()

    # Validar minutos antes de procesar con OpenAI
    if get_minutes(phone) <= 0:
        resp.say("Your time is finished. Goodbye.", voice="alice")
        return Response(content=str(resp), media_type="application/xml")

    # Restamos un minuto y generamos respuesta con IA
    subtract_minute(phone)
    reply = generate_reply(speech)

    # Aviso de último minuto
    if get_minutes(phone) == 1:
        resp.say("Note: You have one minute remaining.", voice="alice")

    # Continuar la conversación
    gather = Gather(input="speech", action="/process", method="POST", speechTimeout="auto", language="en-US")
    gather.say(reply, voice="alice")
    resp.append(gather)
    
    return Response(content=str(resp), media_type="application/xml")

@app.post("/purchase")
async def purchase(request: Request):
    data = await request.json()
    phone = data.get("phone")
    amount = float(data.get("amount", 0))

    # Definimos cuántos minutos dar según el precio
    minutes = {2: 5, 4: 10, 6: 15}.get(amount, 0)

    if minutes > 0:
        add_minutes(phone, minutes)
        # Esto enviará un SMS de confirmación usando Telnyx
        send_sms(phone, f"Thank you! You now have {get_minutes(phone)} minutes in EnglishPower.")

    return {"status": "ok"}
