# config.py
import os

class Config:
    """
    Configuración de entorno para Supabase.
    """
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# Opcional: debug para ver si las variables están cargadas
if __name__ == "__main__":
    print("DEBUG SUPABASE_URL:", Config.SUPABASE_URL)
    print("DEBUG SUPABASE_KEY presente:", bool(Config.SUPABASE_KEY))
