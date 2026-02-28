import os
import uuid
import requests
import telnyx
from flask import Flask, request, jsonify
from openai import OpenAI
from supabase import create_client

app = Flask(__name__)

# =========================
# CONFIGURATION
# =========================
# Keys
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
telnyx.api_key = os.environ.get("TELNYX_API_KEY")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL else None

ELEVEN_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
ELEVEN_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID")

# =========================
# AI LOGIC (Whisper + GPT + ElevenLabs)
# =========================

def process_audio_to_text(audio_url):
    """Downloads audio from Telnyx and transcribes it using OpenAI Whisper"""
    audio_data = requests.get(audio_url).content
    file_path = "temp_recording.mp3"
    with open(file_path, "wb") as f:
        f.write(audio_data)
    
    with open(file_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
    return transcript.text

def generate_ai_reply(text):
    """Generates a conversational response using GPT-3.5/4"""
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are InglesPower, a bilingual English coach. Be brief and encouraging."},
            {"role": "user", "content": text}
        ],
        max_tokens=100
    )
    return response.choices[0].message.content

def get_elevenlabs_audio_url(text):
    """Converts text to speech and uploads to Supabase for Telnyx to play"""
    url = f"https://api.elevenlabs.io{ELEVEN_VOICE_ID}"
    headers = {"xi-api-key": ELEVEN_API_KEY, "Content-Type": "application/json"}
    data = {"text": text, "model_id": "eleven_multilingual_v2"}
    
    response = requests.post(url, json=data, headers=headers)
    if response.status_code != 200: return None

    file_name = f"reply_{uuid.uuid4()}.mp3"
    supabase.storage.from_("audios").upload(path=file_name, file=response.content, file_options={"content-type": "audio/mpeg"})
    return supabase.storage.from_("audios").get_public_url(file_name)

# =========================
# TELNYX WEBHOOK HANDLER
# =========================

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json.get('data', {})
    event_type = data.get('event_type')
    payload = data.get('payload', {})
    call_control_id = payload.get('call_control_id')

    # 1. Answer the call
    if event_type == "call.initiated":
        telnyx.Call.answer(call_control_id=call_control_id)

    # 2. Once answered, ask a question
    elif event_type == "call.answered":
        telnyx.Call.speak(
            call_control_id=call_control_id,
            payload="Hi! I'm your English coach. How can I help you today?",
            voice="female", language="en-US"
        )

    # 3. Start recording after the AI finishes speaking
    elif event_type == "call.speak.ended":
        telnyx.Call.record_start(call_control_id=call_control_id, format="mp3", channels="single")

    # 4. Process the user's speech when recording is saved
    elif event_type == "call.recording.saved":
        recording_url = payload.get('recording_urls', {}).get('mp3')
        
        # TRANSCRIPTION
        user_text = process_audio_to_text(recording_url)
        print(f"User said: {user_text}")

        # GPT RESPONSE
        ai_text = generate_ai_reply(user_text)
        print(f"AI reply: {ai_text}")

        # VOICE GENERATION (ElevenLabs)
        audio_url = get_elevenlabs_audio_url(ai_text)

        # PLAY REPLY IN CALL
        if audio_url:
            telnyx.Call.playback_start(call_control_id=call_control_id, audio_url=audio_url)
        else:
            telnyx.Call.speak(call_control_id=call_control_id, payload=ai_text, voice="female", language="en-US")

    return jsonify({"status": "success"}), 200

if __name__ == '__main__':
    app.run(port=5000)
