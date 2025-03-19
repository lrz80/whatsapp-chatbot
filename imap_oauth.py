import imaplib
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Obtener credenciales desde el .env
EMAIL = os.getenv("GMAIL_EMAIL")
PASSWORD = os.getenv("GMAIL_PASSWORD")

try:
    # Conectar con Gmail IMAP
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(EMAIL, PASSWORD)

    # Seleccionar la bandeja de entrada
    mail.select("inbox")

    # Buscar todos los correos
    status, messages = mail.search(None, "ALL")
    mail_ids = messages[0].split()

    print(f"✅ Conexión exitosa. Correos en bandeja de entrada: {len(mail_ids)}")

    # Cerrar sesión
    mail.logout()

except Exception as e:
    print(f"❌ ERROR: {e}")
