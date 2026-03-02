import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Estas llaves deben estar en la pestaña 'Environment' de Render
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    TELNYX_KEY = os.getenv("TELNYX_API_KEY")
    OPENAI_KEY = os.getenv("OPENAI_API_KEY")
    ELEVEN_KEY = os.getenv("ELEVENLABS_API_KEY")
    VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")
    
    PORT = int(os.getenv("PORT", 10000))
    RECHARGE_URL = "https://invoice-checker--learnengish55.replit.app"
