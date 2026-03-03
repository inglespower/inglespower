from openai import OpenAI
from config import Config

client_openai = OpenAI(api_key=Config.OPENAI_API_KEY)

def generar_respuesta(texto_usuario):
    try:
        response = client_openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system", 
                    "content": "Eres Thorthugo, un tutor de inglés amable. Responde SIEMPRE en español pero enseña inglés. Sé muy breve (máximo 2 frases)."
                },
                {"role": "user", "content": texto_usuario}
            ],
            max_tokens=100
        )
        return response.choices.message.content
    except Exception as e:
        print(f"[ERR AI] {e}")
        return "I'm sorry, can you repeat that?"
