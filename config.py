import os
from dotenv import load_dotenv

# Carga variables desde el entorno de Render o archivo .env local
load_dotenv()

class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
    TELNYX_API_KEY = os.getenv("TELNYX_API_KEY")
    TELNYX_PUBLIC_KEY = os.getenv("TELNYX_PUBLIC_KEY")
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    
    # ID del perfil de mensajería de Telnyx (necesario para SMS)
    TELNYX_MESSAGING_PROFILE_ID = os.getenv("TELNYX_MESSAGING_PROFILE_ID")
