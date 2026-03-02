import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Estas deben coincidir EXACTAMENTE con los nombres en el panel de Render
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    TELNYX_API_KEY = os.getenv("TELNYX_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
    ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")
    
    PORT = int(os.getenv("PORT", 10000))
    RECHARGE_URL = "https://invoice-checker--learnengish55.replit.app"
