import os
import imaplib
import email
from email.header import decode_header
import time

def obtener_codigo_glofox():
    """ Obtiene el código de verificación de Glofox desde Gmail. """
    EMAIL = os.getenv("GMAIL_EMAIL", "spinzonechatbot@gmail.com")
    PASSWORD = os.getenv("GMAIL_PASSWORD")  # Si usas 2FA, usa una contraseña de aplicación

    try:
        print("📩 Conectando a la cuenta de Gmail para obtener el código...")

        # Conexión IMAP a Gmail
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL, PASSWORD)
        mail.select("inbox")

        # Buscar correos con el remitente de Glofox
        result, data = mail.search(None, '(FROM "noreply@glofox.com")')
        mail_ids = data[0].split()

        if not mail_ids:
            print("❌ No se encontró un correo de verificación de Glofox.")
            return None

        # Leer el último correo recibido
        latest_email_id = mail_ids[-1]
        result, data = mail.fetch(latest_email_id, "(RFC822)")
        raw_email = data[0][1]
        msg = email.message_from_bytes(raw_email)

        # Extraer el cuerpo del email
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode()
                    break
        else:
            body = msg.get_payload(decode=True).decode()

        # 📌 IMPRIMIR el contenido del correo recibido para depuración
        print("\n📩 **Contenido del último correo recibido:**\n")
        print(body)
        print("\n📩 **Fin del contenido del correo**\n")

        # Buscar el código en el correo
        match = re.search(r"Verification code: (\d{6})", body)
        if match:
            codigo = match.group(1)
            print(f"✅ Código de verificación encontrado: {codigo}")
            return codigo
        else:
            print("❌ No se encontró un código de verificación en el correo.")
            return None

    except Exception as e:
        print(f"❌ Error al obtener código de Glofox: {e}")
        return None
