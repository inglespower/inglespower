import telnyx
from config import Config

telnyx.api_key = Config.TELNYX_API_KEY

def enviar_sms_saldo_bajo(telefono_cliente):
    """Envía un aviso cuando el cliente intenta llamar sin minutos."""
    try:
        telnyx.Message.create(
            from_="+1XXXXXXXXXX", # Tu número de Telnyx
            to=telefono_cliente,
            text="Tu saldo de minutos se ha agotado. Recarga en nuestra web para seguir practicando.",
            messaging_profile_id=Config.TELNYX_MESSAGING_PROFILE_ID
        )
        return True
    except Exception as e:
        print(f"Error enviando SMS: {e}")
        return False

def enviar_resumen_practica(telefono_cliente, resumen):
    """Opcional: envía un resumen de la práctica por SMS."""
    telnyx.Message.create(
        from_="+1XXXXXXXXXX",
        to=telefono_cliente,
        text=f"Resumen de tu práctica: {resumen}",
        messaging_profile_id=Config.TELNYX_MESSAGING_PROFILE_ID
    )
