import os
import uuid
import requests
from fastapi import FastAPI, Request, Response
from openai import OpenAI
from supabase import create_client
import telnyx

from ai import generate_reply, get_voice_audio_url
from supabase_client import get_minutes, subtract_minute

# =========================
# CONFIGURACIÓN CLIENTES
# =========================
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
telnyx.api_key = os.environ.get("TELNYX_API_KEY")
TELNYX_PHONE_NUMBER = os.environ.get("TELNYX_PHONE_NUMBER")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()


# ==========================================
# FUNCIONES AUXILIARES
# ==========================================
def transcribe_audio(url):
    try:
        audio_data = requests.get(url).content
        temp_filename = f"/tmp/{uuid.uuid4()}.mp3"
        with open(temp_filename, "wb") as f:
            f.write(audio_data)
        
        with open(temp_filename, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file
            )
        return transcript.text
    except Exception as e:
        print(f"Error en transcripción: {e}")
        return None


# ==========================================
# WEBHOOK PRINCIPAL
# ==========================================
@app.post("/webhook")
async def telnyx_webhook(request: Request):
    # Telnyx envía application/x-www-form-urlencoded, no JSON
    form = await request.form()
    form_dict = dict(form)
    
    event_type = form_dict.get("EventType") or form_dict.get("event_type")
    call_control_id = form_dict.get("CallControlId") or form_dict.get("call_control_id")
    from_phone = form_dict.get("From")
    
    # 1. Contestar la llamada
    if event_type == "call.initiated":
        telnyx.Call.answer(call_control_id=call_control_id)

    # 2. Saludo inicial
    elif event_type == "call.answered":
        minutes = get_minutes(from_phone)
        if minutes <= 0:
            telnyx.Call.speak(
                call_control_id=call_control_id,
                payload="You have no minutes left. Please recharge. Goodbye.",
                voice="female", language="en-US"
            )
        else:
            telnyx.Call.speak(
                call_control_id=call_control_id,
                payload="Hello! I'm your English coach. How can I help you practice today?",
                voice="female", language="en-US"
            )

    # 3. Grabar usuario
    elif event_type in ["call.speak.ended", "call.playback.ended"]:
        telnyx.Call.record_start(
            call_control_id=call_control_id,
            format="mp3",
            channels="single",
            play_beep=True,
            limit_seconds=15
        )

    # 4. Procesar grabación
    elif event_type == "call.recording.saved":
        recording_url = form_dict.get("RecordingUrl") or form_dict.get("recording_urls")
        if recording_url:
            user_text = transcribe_audio(recording_url)
            if user_text:
                subtract_minute(from_phone)
                reply_text = generate_reply(user_text)
                audio_url = get_voice_audio_url(reply_text)
                if audio_url:
                    telnyx.Call.playback_start(
                        call_control_id=call_control_id,
                        audio_url=audio_url
                    )
                else:
                    telnyx.Call.speak(
                        call_control_id=call_control_id,
                        payload=reply_text,
                        voice="female",
                        language="en-US"
                    )
            else:
                telnyx.Call.speak(
                    call_control_id=call_control_id,
                    payload="I didn't catch that. Please try again.",
                    voice="female",
                    language="en-US"
                )

    return Response(status_code=200)


# ==========================================
# EJECUCIÓN EN RENDER
# ==========================================
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port, timeout_keep_alive=60)
