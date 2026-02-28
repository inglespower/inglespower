import telnyx
import os

# Telnyx usa estas llaves que ya configuramos en Render
telnyx.api_key = os.getenv("TELNYX_API_KEY")
TELNYX_PHONE_NUMBER = os.getenv("TELNYX_PHONE_NUMBER")

def send_sms(to, body):
    # Esta función enviará el mensaje usando tu saldo de Telnyx
    return telnyx.Message.create(
        from_=TELNYX_PHONE_NUMBER,
        to=to,
        text=body
    )
