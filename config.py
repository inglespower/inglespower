import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
    # ID de voz de Thorthugo
    VOICE_ID = "WOY6pnQ1WCg0mrOZ54lM" 
    TELNYX_API_KEY = os.getenv("TELNYX_API_KEY")
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    
    # Limpia el dominio automáticamente para que el WebSocket no falle
    raw_domain = os.getenv("DOMAIN", "inglespower.onrender.com")
    DOMAIN = raw_domain.replace("https://", "").replace("http://", "").strip("/")
