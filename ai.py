import openai
from config import OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY

def generate_reply(user_text):
system = """
You are InglesPower, a bilingual English coach for Spanish speakers in the U.S.
You are friendly, patient, and practical.
Help with:
- work conversations
- daily life
- pronunciation
- correction
- motivation
Switch automatically between English and Spanish.
Keep responses short and natural.
Always ask a follow-up question.
"""

resp = openai.ChatCompletion.create(
model="gpt-3.5-turbo",
messages=[
{"role":"system","content":system},
{"role":"user","content":user_text}
],
max_tokens=120
)

return resp.choices[0].message.content
