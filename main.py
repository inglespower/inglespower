import os
from fastapi import FastAPI, Request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather
from supabase_client import get_minutes, subtract_minute, add_minutes
from twilio_client import send_sms 
from ai import generate_reply, get_nathaniel_voice_url

app = FastAPI()

@app.post("/voice")
async def voice(request: Request):
    form = await request.form()
    phone = form.get("From") or form.get("from")
    resp = VoiceResponse()

    # 1. VERIFICACIÓN DE MINUTOS
    minutes = get_minutes(phone)
    if minutes <= 0:
        resp.say("You have no minutes. Please recharge your account at our website. Thank you.", voice="alice")
        return Response(content=str(resp), media_type="application/xml")

    # 2. SALUDO INICIAL (MEJORADO)
    # Agregamos speechTimeout="3" y profanityFilter="false" para mejor captura
    gather = Gather(
        input="speech", 
        action="/process", 
        method="POST", 
        speechTimeout="3",      # Espera 3 segundos de silencio antes de procesar
        language="en-US", 
        enhanced=True,          # Mayor calidad de reconocimiento
        speechModel="phone_call" # Optimizado para llamadas telefónicas
    )
    gather.say("Hello! I am your English Power coach. How can I help you practice today?", voice="alice")
    resp.append(gather)
    
    return Response(content=str(resp), media_type="application/xml")

@app.post("/process")
async def process(request: Request):
    form = await request.form()
    phone = form.get("From") or form.get("from")
    speech = form.get("SpeechResult", "") # Aquí llega lo que dijiste
    resp = VoiceResponse()

    # Si Twilio no entendió nada, volvemos a preguntar en lugar de fallar
    if not speech:
        gather = Gather(input="speech", action="/process", method="POST", speechTimeout="3", language="en-US")
        gather.say("I'm sorry, I didn't catch that. Could you repeat it?", voice="alice")
        resp.append(gather)
        return Response(content=str(resp), media_type="application/xml")

    # 3. VALIDAR MINUTOS
    if get_minutes(phone) <= 0:
        resp.say("Your time is finished. Goodbye.", voice="alice")
        return Response(content=str(resp), media_type="application/xml")

    # 4. RESTAMOS EL MINUTO
    subtract_minute(phone)
    
    # 5. GENERAR RESPUESTA Y AUDIO
    reply_text = generate_reply(speech)
    audio_url = get_nathaniel_voice_url(reply_text)

    # 6. AVISO DE ÚLTIMO MINUTO
    if get_minutes(phone) == 1:
        resp.say("Note: You have one minute remaining.", voice="alice")

    # 7. CONTINUAR CONVERSACIÓN (MEJORADO)
    gather = Gather(
        input="speech", 
        action="/process", 
        method="POST", 
        speechTimeout="3", 
        language="en-US",
        enhanced=True,
        speechModel="phone_call"
    )
    
    if audio_url:
        gather.play(audio_url)
    else:
        # Respaldo si falla ElevenLabs
        gather.say(reply_text, voice="alice")
        
    resp.append(gather)
    
    return Response(content=str(resp), media_type="application/xml")
