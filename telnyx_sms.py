import telnyx
from config import Config

telnyx.api_key = Config.TELNYX_API_KEY

def enviar_sms(destinatario, mensaje):
    try:
        telnyx.Message.create(
            from_="+1XXXXXXXXXX", # Tu número de Telnyx comprado
            to=destinatario,
            text=mensaje,
            messaging_profile_id=Config.TELNYX_MESSAGING_PROFILE_ID
        )
    except Exception as e:
        print(f"Error al enviar SMS: {e}")
