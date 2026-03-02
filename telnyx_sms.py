import telnyx
from config import Config

telnyx.api_key = Config.TELNYX_API_KEY

def enviar_sms_recarga(numero):
    telnyx.Message.create(
        from_="+1XXXXXXXXXX", # Tu numero de Telnyx
        to=numero,
        text=f"Te has quedado sin minutos para tu tutor de inglés. Recarga aquí: {Config.RECHARGE_URL}"
    )
