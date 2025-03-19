import imaplib
import email
import os
from email.header import decode_header

def obtener_codigo_glofox():
    print("📩 Intentando conectar a Gmail...")

    EMAIL = "spinzonechatbot@gmail.com"
    PASSWORD = "blrubukfuzptprpa"

    print(f"📩 Usando email: {EMAIL}")

    try:
        print("🔄 Intentando conexión a Gmail IMAP...")
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL, PASSWORD)
        mail.select("inbox")
        print("✅ Conexión a Gmail exitosa.")

        result, data = mail.search(None, 'ALL')
        mail_ids = data[0].split()

        if not mail_ids:
            print("❌ No hay correos en la bandeja de entrada.")
        else:
            print(f"📩 Se encontraron {len(mail_ids)} correos en la bandeja de entrada.")
    
        # Leer el último correo
        latest_email_id = mail_ids[-1]
        result, data = mail.fetch(latest_email_id, "(RFC822)")
        raw_email = data[0][1]
        msg = email.message_from_bytes(raw_email)

        print(f"📩 Asunto del último correo: {msg['Subject']}")

    except Exception as e:
        print(f"❌ Error al conectar a Gmail: {e}")
