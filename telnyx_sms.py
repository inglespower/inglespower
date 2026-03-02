from telnyx import Telnyx
from config import Config

# INICIALIZACIÓN MODERNA (V4)
client = Telnyx(api_key=Config.TELNYX_API_KEY)

def enviar_sms(destinatario, mensaje):
    try:
        # CORRECCIÓN: Usamos client.messages.create en lugar de telnyx.Message.create
        client.messages.create(
            from_="+1XXXXXXXXXX", # REEMPLAZA CON TU NÚMERO DE TELNYX
            to=destinatario,
            text=mensaje,
            messaging_profile_id=Config.TELNYX_MESSAGING_PROFILE_ID
        )
        print(f"SMS enviado a {destinatario}")
    except Exception as e:
        print(f"Error al enviar SMS: {e}")
