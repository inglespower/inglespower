import os
import openai
import requests
import uuid
from flask import Flask, request, jsonify
from supabase import create_client

####################################
# CONFIG
####################################

app = Flask(__name__)

openai.api_key = os.environ.get("OPENAI_API_KEY","").strip()

TELNYX_API_KEY = os.environ.get("TELNYX_API_KEY","").strip()

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY","").strip()
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID","").strip()

SUPABASE_URL = os.environ.get("SUPABASE_URL","").strip()
SUPABASE_KEY = os.environ.get("SUPABASE_KEY","").strip()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


####################################
# OPENAI
####################################

def generate_reply(user_text):

    system = """
You are InglesPower AI.

You teach English.

Rules:

Be short.
Ask simple questions.
Correct English.
Wait for answer.
"""

    try:

        response = openai.ChatCompletion.create(

            model="gpt-3.5-turbo",

            messages=[

                {"role":"system","content":system},

                {"role":"user","content":user_text}

            ],

            max_tokens=120

        )

        return response.choices[0].message.content

    except Exception as e:

        print("OpenAI error:",e)

        return "Say another word in English."


####################################
# ELEVENLABS VOICE
####################################

def generate_voice(text):

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"

    headers = {

        "xi-api-key": ELEVENLABS_API_KEY,

        "Content-Type":"application/json"

    }

    data = {

        "text":text,

        "model_id":"eleven_multilingual_v2",

        "voice_settings":{

            "stability":0.5,

            "similarity_boost":0.75

        }

    }

    response = requests.post(

        url,

        json=data,

        headers=headers,

        timeout=30

    )

    file_name = f"voice_{uuid.uuid4()}.mp3"


    supabase.storage.from_("audios").upload(

        path=file_name,

        file=response.content,

        file_options={"content-type":"audio/mpeg"}

    )


    public_url = supabase.storage.from_("audios").get_public_url(file_name)

    return public_url


####################################
# TELNYX COMMAND
####################################

def telnyx_command(call_id,command,payload={}):

    url = f"https://api.telnyx.com/v2/calls/{call_id}/actions/{command}"

    headers = {

        "Authorization":f"Bearer {TELNYX_API_KEY}",

        "Content-Type":"application/json"

    }

    requests.post(

        url,

        json=payload,

        headers=headers

    )


####################################
# WEBHOOK
####################################

@app.route("/",methods=["POST"])
def webhook():

    data = request.json

    event = data["data"]["event_type"]

    call_id = data["data"]["payload"]["call_control_id"]

    print("EVENT:",event)


####################################
# ANSWER CALL
####################################

    if event == "call.initiated":

        telnyx_command(call_id,"answer")

        return jsonify({"ok":True})


####################################
# FIRST MESSAGE
####################################

    if event == "call.answered":

        welcome = "Hello. Welcome to Ingles Power. Say a word in English."

        audio_url = generate_voice(welcome)

        telnyx_command(call_id,"playback_start",{

            "audio_url":audio_url

        })


        telnyx_command(call_id,"gather_using_speech",{

            "language":"en-US",

            "max_silence":5,

            "speech_timeout":5

        })

        return jsonify({"ok":True})


####################################
# SPEECH RESULT
####################################

    if event == "call.speech.recognition.result":

        user_text = data["data"]["payload"]["transcription"]

        print("USER:",user_text)


        reply = generate_reply(user_text)

        print("AI:",reply)


        audio_url = generate_voice(reply)


        telnyx_command(call_id,"playback_start",{

            "audio_url":audio_url

        })


        telnyx_command(call_id,"gather_using_speech",{

            "language":"en-US",

            "max_silence":5,

            "speech_timeout":5

        })


        return jsonify({"ok":True})


    return jsonify({"ok":True})


####################################
# SERVER
####################################

if __name__ == "__main__":

    app.run(host="0.0.0.0",port=10000)
