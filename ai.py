from openai import OpenAI
from config import Config

client = OpenAI(api_key=Config.OPENAI_API_KEY)

def generar_respuesta(texto_usuario):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Eres un tutor de inglés nativo. Sé amable, breve y corrige los errores del usuario de forma sutil."},
            {"role": "user", "content": texto_usuario}
        ]
    )
    return response.choices.message.content
