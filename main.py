import os
from fastapi import FastAPI, Request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather
from supabase_client import get_minutes, subtract_minute, add_minutes
from twilio_client import send_sms 
from ai import generate_reply, get_nathaniel_voice_url # Importamos ambas de tu ai.py

app = FastAPI()

@app.post("/voice")
async def voice(request: Request):
    form = await request.form()
    phone = form.get("From") or form.get("from")
    resp = VoiceResponse()

    # 1. VERIFICACIÓN DE MINUTOS (TU LÓGICA DE NEGOCIO)
    minutes = get_minutes(phone)
    if minutes <= 0:
        resp.say("You have no minutes. Please recharge your account at our website. Thank you.", voice="alice")
        return Response(content=str(resp), media_type="application/xml")

    # 2. SALUDO INICIAL
    gather = Gather(input="speech", action="/process", method="POST", speechTimeout="auto", language="en-US")
    gather.say("Hello! I am your English Power coach. How can I help you practice today?", voice="alice")
    resp.append(gather)
    
    return Response(content=str(resp), media_type="application/xml")

@app.post("/process")
async def process(request: Request):
    form = await request.form()
    phone = form.get("From") or form.get("from")
    speech = form.get("SpeechResult", "")
    resp = VoiceResponse()

    # 3. VALIDAR MINUTOS ANTES DE PROCESAR CON IA
    if get_minutes(phone) <= 0:
        resp.say("Your time is finished. Goodbye.", voice="alice")
        return Response(content=str(resp), media_type="application/xml")

    # 4. RESTAMOS EL MINUTO EN SUPABASE
    subtract_minute(phone)
    
    # 5. GENERAR RESPUESTA Y AUDIO CON NATHANIEL
    # Obtenemos el texto de OpenAI
    reply_text = generate_reply(speech)
    # Obtenemos la URL del audio de ElevenLabs subido a Supabase Storage
    audio_url = get_nathaniel_voice_url(reply_text)

    # 6. AVISO DE ÚLTIMO MINUTO
    if get_minutes(phone) == 1:
        resp.say("Note: You have one minute remaining.", voice="alice")

    # 7. CONTINUAR CONVERSACIÓN (AQUÍ HABLA NATHANIEL)
    gather = Gather(input="speech", action="/process", method="POST", speechTimeout="auto", language="en-US")
    
    if audio_url:
        # Si todo salió bien, Telnyx reproduce el audio real de Nathaniel
        gather.play(audio_url)
    else:
        # RESPALDO: Si ElevenLabs o la subida fallan, usamos Alice para no colgar
        gather.say(reply_text, voice="alice")
        
    resp.append(gather)
    
    return Response(content=str(resp), media_type="application/xml")

@app.post("/purchase")
async def purchase(request: Request):
    """TU LÓGICA DE COMPRA ORIGINAL"""
    data = await request.json()
    phone = data.get("phone")
    amount = float(data.get("amount", 0))

    # Definimos cuántos minutos dar según el precio
    minutes_added = {2: 5, 4: 10, 6: 15}.get(amount, 0)

    if minutes_added > 0:
        add_minutes(phone, minutes_added)
        send_sms(phone, f"Thank you! You now have {get_minutes(phone)} minutes in EnglishPower.")

    return {"status": "ok"}

if __name__ == "__main__":
    # Render usa el puerto 10000
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
