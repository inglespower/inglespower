from openai import OpenAI
from config import Config

# Solo necesitamos OpenAI aquí para pensar la respuesta
client_openai = OpenAI(api_key=Config.OPENAI_API_KEY)

def generar_respuesta(texto_usuario):
    """
    Cerebro de Thorthugo: Recibe texto, devuelve texto.
    Sin archivos, sin demoras.
    """
    try:
        response = client_openai.chat.completions.create(
            model="gpt-4o-mini", # Ultra rápido para voz
            messages=[
                {
                    "role": "system", 
                    "content": (
                        "Eres Thorthugo, un tutor de inglés amable. "
                        "RESPONDE SIEMPRE EN ESPAÑOL pero enseña frases en inglés. "
                        "Sé muy breve (máximo 2 frases) para latencia baja."
                    )
                },
                {"role": "user", "content": texto_usuario}
            ],
            max_tokens=100
        )
        return response.choices.message.content
    except Exception as e:
        print(f"[ERROR AI.PY] {e}")
        return "I'm sorry, can you repeat that?"
