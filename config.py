import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
    # Esta es la variable que debes tener en Render
    ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID") 
    TELNYX_API_KEY = os.getenv("TELNYX_API_KEY")
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    PORT = int(os.getenv("PORT", 10000))
