import imaplib
import email
import re
from bs4 import BeautifulSoup

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

        # Buscar correos recientes
        resultado, mensajes = mail.search(None, 'ALL')
        if resultado != "OK":
            print("❌ No se pudieron recuperar los correos.")
            return None

        mail_ids = mensajes[0].split()
        if not mail_ids:
            print("❌ No hay correos en la bandeja de entrada.")
            return None

        # Buscar en los últimos 5 correos
        codigo = None
        for email_id in reversed(mail_ids[-5:]):
            result, data = mail.fetch(email_id, "(RFC822)")
            if result != "OK":
                print("❌ No se pudo obtener el contenido del correo.")
                continue

            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)
            subject = msg["Subject"] or "(Sin asunto)"

            print(f"📩 Asunto del correo: {subject}")

            # Buscar palabras clave en el asunto del correo
            if any(keyword in subject.lower() for keyword in ["verification code", "security code", "your unique login code"]):
                print("✅ Encontrado un correo con código de verificación. Leyendo contenido...")

                body = None

                # Extraer contenido del correo
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode(errors="ignore")
                        break
                    elif part.get_content_type() == "text/html":
                        body = part.get_payload(decode=True).decode(errors="ignore")

                if body:
                    print(f"📩 Cuerpo del correo (antes de limpiar HTML):\n{body}")

                    # Limpiar HTML y extraer texto puro
                    soup = BeautifulSoup(body, "html.parser")
                    texto_limpio = soup.get_text()
                    print(f"📩 Cuerpo del correo (después de limpiar HTML):\n{texto_limpio}")

                    # Buscar código de verificación (6 dígitos)
                    match = re.search(r'\b\d{6}\b', texto_limpio)
                    if match:
                        codigo = match.group(0)
                        print(f"✅ Código de verificación encontrado: {codigo}")
                        return codigo
                    else:
                        print("❌ No se encontró un código de 6 dígitos en este correo.")
                else:
                    print("❌ No se pudo extraer el cuerpo del correo.")

        print("❌ No se encontró ningún código en los últimos correos.")

    except Exception as e:
        print(f"❌ Error al conectar a Gmail: {e}")
        return None

if __name__ == "__main__":
    codigo = obtener_codigo_glofox()
    print(f"✅ Código obtenido: {codigo}" if codigo else "❌ No se encontró ningún código.")
