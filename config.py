import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Usamos .get() para evitar el error 'required' si Render tarda en cargar
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    TELNYX_API_KEY = os.environ.get("TELNYX_API_KEY")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
    ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID")
    RECHARGE_URL = "https://invoice-checker--learnengish55.replit.app"
