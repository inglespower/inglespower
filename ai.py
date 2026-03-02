import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def obtener_respuesta_ai(prompt_usuario):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Eres un tutor de idiomas servicial. Habla de forma natural y breve."},
            {"role": "user", "content": prompt_usuario}
        ]
    )
    return response.choices[0].message.content
