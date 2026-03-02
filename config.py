# config.py
import os

class Config:
    """
    Configuración de entorno para Supabase.
    Lee las variables de entorno SUPABASE_URL y SUPABASE_KEY.
    Si no existen, deja cadenas vacías.
    """
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# Debug opcional: imprime si las variables fueron cargadas correctamente
if __name__ == "__main__":
    print("DEBUG SUPABASE_URL:", SUPABASE_URL := Config.SUPABASE_URL)
    print("DEBUG SUPABASE_KEY presente:", bool(Config.SUPABASE_KEY))
