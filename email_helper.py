import os
import imaplib
import email
from email.header import decode_header
import time

# Cargar variables de entorno
EMAIL = os.getenv("OUTLOOK_EMAIL")
APP_PASSWORD = os.getenv("OUTLOOK_APP_PASSWORD")
IMAP_SERVER = "outlook.office365.com"

def obtener_codigo_glofox():
    """Conecta a Outlook vía IMAP y extrae el código de verificación de Glofox."""
    try:
        print("🔍 Buscando código de verificación en Outlook...")
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL, APP_PASSWORD)
        mail.select("inbox")

        # Buscar los correos más recientes con "Glofox" en el asunto
        _, messages = mail.search(None, '(FROM "no-reply@glofox.com" SUBJECT "Your two-step verification code")')

        if not messages[0]:
            print("❌ No se encontró un correo de verificación de Glofox.")
            return None

        latest_email_id = messages[0].split()[-1]  # Último email recibido

        _, msg_data = mail.fetch(latest_email_id, "(RFC822)")
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                body = ""

                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        if content_type == "text/plain":
                            body = part.get_payload(decode=True).decode()
                else:
                    body = msg.get_payload(decode=True).decode()

                # Extraer código de verificación (asumiendo que es un número de 6 dígitos en el correo)
                import re
                match = re.search(r'\b\d{6}\b', body)
                if match:
                    code = match.group(0)
                    print(f"📩 Código recibido: {code}")
                    return code

        mail.logout()
        return None
    except Exception as e:
        print(f"❌ Error al obtener el código de Glofox: {e}")
        return None
