import imaplib
import email
from email.header import decode_header

# Datos de la cuenta de Gmail
USERNAME = "spinzonechatbot@gmail.com"  # Tu correo
PASSWORD = "blrubukfuzptprpa"  # Tu contraseña de aplicación

try:
    # Conectar a Gmail con IMAP
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(USERNAME, PASSWORD)
    print("✅ Conexión a Gmail exitosa.")

    # Seleccionar la bandeja de entrada
    mail.select("inbox")

    # Buscar los últimos 5 correos para verificar acceso
    result, data = mail.search(None, "ALL")
    mail_ids = data[0].split()[-5:]  # Tomar los últimos 5 correos

    for mail_id in reversed(mail_ids):
        result, msg_data = mail.fetch(mail_id, "(RFC822)")
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding or "utf-8")

                print(f"📩 Asunto del correo: {subject}")

except Exception as e:
    print(f"❌ ERROR al conectar a Gmail: {e}")
