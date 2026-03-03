import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
    VOICE_ID = "WOY6pnQ1WCg0mrOZ54lM" # Tu ID de Thorthugo
    TELNYX_API_KEY = os.getenv("TELNYX_API_KEY")
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    # URL de tu app (ej: inglespower.onrender.com)
    DOMAIN = os.getenv("DOMAIN", "inglespower.onrender.com") 
