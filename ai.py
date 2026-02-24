import openai
from config import OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY

def generate_reply(user_text):
    system = """
    You are InglesPower, a bilingual English coach...
    """
    resp = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_text}
        ],
        max_tokens=120
    )
    return resp.choices[0].message.content
