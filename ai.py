from openai import OpenAI
from config import Config

# Solo necesitamos OpenAI aquí para pensar la respuesta
client_openai = OpenAI(api_key=Config.OPENAI_API_KEY)

def generar_respuesta(texto_usuario):
    """
    Genera una respuesta breve de tutor de inglés.
    Diseñado para ser ultra rápido en streaming.
    """
    try:
        # Usamos gpt-4o-mini porque es 10 veces más rápido para voz
        response = client_openai.chat.completions.create(
            model="gpt-4o-mini", 
            messages=[
                {
                    "role": "system", 
                    "content": (
                        "Eres Thorthugo, un tutor de inglés amable. "
                        "RESPONDE SIEMPRE EN ESPAÑOL pero enseña frases en inglés. "
                        "Sé muy breve (máximo 2 frases) para que la voz no tarde en cargar."
                    )
                },
                {"role": "user", "content": texto_usuario}
            ],
            max_tokens=100,
            temperature=0.7
        )
        return response.choices.message.content
    except Exception as e:
        print(f"[ERROR AI.PY] OpenAI: {e}")
        return "Lo siento, tuve un problema técnico. ¿Puedes repetir?"

# NOTA: La función texto_a_voz ha sido eliminada de aquí 
# porque el audio ahora se genera en tiempo real en el main.py
