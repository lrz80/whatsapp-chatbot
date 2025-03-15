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
    try:
        print("📩 Buscando código de verificación en el correo...")

        OUTLOOK_EMAIL = os.getenv("OUTLOOK_EMAIL")
        OUTLOOK_APP_PASSWORD = os.getenv("OUTLOOK_APP_PASSWORD")
        IMAP_SERVER = os.getenv("IMAP_SERVER", "outlook.office365.com")

        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(OUTLOOK_EMAIL, OUTLOOK_APP_PASSWORD)
        mail.select("inbox")

        _, messages = mail.search(None, "ALL")
        email_ids = messages[0].split()

        for email_id in reversed(email_ids):
            _, msg_data = mail.fetch(email_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding or "utf-8")

                    if "Glofox" in subject:
                        print(f"📨 Email encontrado: {subject}")
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                content_type = part.get_content_type()
                                if content_type == "text/plain":
                                    body = part.get_payload(decode=True).decode()
                        else:
                            body = msg.get_payload(decode=True).decode()

                        for line in body.split("\n"):
                            if line.strip().isdigit() and len(line.strip()) == 6:
                                print(f"✅ Código encontrado: {line.strip()}")
                                return line.strip()

        print("❌ No se encontró código de verificación en el correo.")
        mail.logout()
        return None
    except Exception as e:
        print(f"❌ Error al obtener código de Glofox: {e}")
        return None
