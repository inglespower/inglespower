import os
from fastapi import FastAPI, Request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather
from supabase_client import get_minutes, subtract_minute, add_minutes
from twilio_client import send_sms 
from ai import generate_reply, get_nathaniel_voice_url # Importamos ambas funciones

app = FastAPI()

@app.post("/voice")
async def voice(request: Request):
    form = await request.form()
    phone = form.get("From") or form.get("from")
    resp = VoiceResponse()

    # 1. Verificamos minutos en Supabase (TU LÓGICA ORIGINAL)
    minutes = get_minutes(phone)
    if minutes <= 0:
        resp.say("You have no minutes. Please recharge your account at our website. Thank you.", voice="alice")
        return Response(content=str(resp), media_type="application/xml")

    # 2. Gather para capturar la voz del usuario
    gather = Gather(input="speech", action="/process", method="POST", speechTimeout="auto", language="en-US")
    # Saludo inicial (puedes cambiarlo a Nathaniel después si quieres)
    gather.say("Hello! I am your English Power coach. How can I help you practice today?", voice="alice")
    resp.append(gather)
    
    return Response(content=str(resp), media_type="application/xml")

@app.post("/process")
async def process(request: Request):
    form = await request.form()
    phone = form.get("From") or form.get("from")
    speech = form.get("SpeechResult", "")
    resp = VoiceResponse()

    # 3. Validar minutos antes de procesar
    if get_minutes(phone) <= 0:
        resp.say("Your time is finished. Goodbye.", voice="alice")
        return Response(content=str(resp), media_type="application/xml")

    # 4. Restamos un minuto
    subtract_minute(phone)
    
    # 5. GENERAR RESPUESTA Y AUDIO (NATHANIEL)
    reply_text = generate_reply(speech)
    audio_url = get_nathaniel_voice_url(reply_text)

    # 6. Aviso de último minuto
    if get_minutes(phone) == 1:
        resp.say("Note: You have one minute remaining.", voice="alice")

    # 7. Continuar la conversación con GATHER
    gather = Gather(input="speech", action="/process", method="POST", speechTimeout="auto", language="en-US")
    
    if audio_url:
        # AQUÍ NATHANIEL HABLA SI ELEVENLABS Y SUPABASE STORAGE FUNCIONAN
        gather.play(audio_url)
    else:
        # RESPALDO: Si falla el audio, usamos la voz robótica para que no se corte la llamada
        gather.say(reply_text, voice="alice")
        
    resp.append(gather)
    
    return Response(content=str(resp), media_type="application/xml")

@app.post("/purchase")
async def purchase(request: Request):
    data = await request.json()
    phone = data.get("phone")
    amount = float(data.get("amount", 0))

    # Lógica de precios original
    minutes_to_add = {2: 5, 4: 10, 6: 15}.get(amount, 0)

    if minutes_to_add > 0:
        add_minutes(phone, minutes_to_add)
        send_sms(phone, f"Thank you! You now have {get_minutes(phone)} minutes in EnglishPower.")

    return {"status": "ok"}
