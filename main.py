import os
from fastapi import FastAPI, Request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather
from supabase_client import get_minutes, subtract_minute, add_minutes
from twilio_client import send_sms 
from ai import generar_respuesta_ia # Cambié el nombre a la función que definimos en ai.py

app = FastAPI()

@app.post("/voice")
async def voice(request: Request):
    form = await request.form()
    # Telnyx a veces envía 'From' o 'Caller'
    phone = form.get("From") or form.get("Caller") or "unknown"
    
    resp = VoiceResponse()

    # 1. Validación de minutos en Supabase
    try:
        minutes = get_minutes(phone)
    except:
        minutes = 0 # Fallback si falla la DB

    if minutes <= 0:
        resp.say("You have no minutes. Please recharge your account at our website. Thank you.", voice="alice")
        return Response(content=str(resp), media_type="application/xml")

    # 2. GATHER: Clave para que no se corte
    # Añadimos 'actionOnEmptyResult' para que si el usuario no habla, no se cuelgue
    gather = Gather(
        input="speech", 
        action="/process", 
        method="POST", 
        speechTimeout="auto", 
        language="en-US",
        actionOnEmptyResult=True 
    )
    gather.say("Hello! I am your English Power coach. How can I help you practice today?", voice="alice")
    resp.append(gather)
    
    # Si el gather falla o el usuario no dice nada, redirigimos para no colgar
    resp.redirect("/voice") 
    
    return Response(content=str(resp), media_type="application/xml")

@app.post("/process")
async def process(request: Request):
    form = await request.form()
    phone = form.get("From") or form.get("Caller") or "unknown"
    speech = form.get("SpeechResult", "")
    
    resp = VoiceResponse()

    # Si no hubo audio detectado, volvemos a preguntar
    if not speech:
        resp.redirect("/voice")
        return Response(content=str(resp), media_type="application/xml")

    # 3. Lógica de minutos y AI
    current_minutes = get_minutes(phone)
    if current_minutes <= 0:
        resp.say("Your time is finished. Goodbye.", voice="alice")
        return Response(content=str(resp), media_type="application/xml")

    subtract_minute(phone)
    
    # Llamamos a la IA (Asegúrate que en ai.py se llame generar_respuesta_ia)
    try:
        reply = generar_respuesta_ia(speech)
    except:
        reply = "I'm sorry, I'm having a connection issue. Can you repeat that?"

    if current_minutes == 1:
        resp.say("Note: You have one minute remaining.", voice="alice")

    # 4. Continuar la conversación
    gather = Gather(
        input="speech", 
        action="/process", 
        method="POST", 
        speechTimeout="auto", 
        language="en-US"
    )
    gather.say(reply, voice="alice")
    resp.append(gather)
    
    # Redirección de seguridad
    resp.redirect("/voice")
    
    return Response(content=str(resp), media_type="application/xml")
