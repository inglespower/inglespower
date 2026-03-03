import telnyx
from config import Config

# Configuración v3
telnyx.api_key = Config.TELNYX_API_KEY

def enviar_link_pago(phone_number):
    """Envía SMS con link de pago si el usuario no tiene minutos."""
    try:
        # Reemplaza con tu link real de Stripe/PayPal
        pago_url = "https://tu-sitio.com"
        mensaje = f"Thorthugo: Te has quedado sin minutos. Recarga aquí para seguir practicando: {pago_url}"

        # SINTAXIS v3
        telnyx.Message.create(
            from_="+12029604000", # Reemplaza por tu número de Telnyx con SMS activo
            to=phone_number,
            text=mensaje
        )
        print(f"[SMS] Link enviado a {phone_number}")
        return True
    except Exception as e:
        print(f"[ERR SMS] {e}")
        return False
