import uvicorn
import os
import imaplib
import email
import time
import gspread
import json
import shutil
import asyncio
import aiohttp
import tempfile
import openai
import requests
from fastapi import FastAPI, Request, Form
from fastapi.responses import Response, PlainTextResponse
from starlette.requests import ClientDisconnect
from fastapi import FastAPI, Request
from openai import OpenAI
from twilio.twiml.messaging_response import MessagingResponse
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from twilio.rest import Client
from langdetect import detect
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from email.header import decode_header
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from google.oauth2.service_account import Credentials

# Cargar variables de entorno
load_dotenv()

# 🔴 No iniciar WebDriver aquí (Evita errores en Railway)
# El WebDriver se iniciará dentro de la función `gestionar_reserva_glofox()`

# 🛑 Función para cerrar procesos previos de Chrome (evita conflictos)
def cerrar_chromedriver():
    if os.name == "posix":  # Linux/macOS (Railway)
        os.system("pkill -f chromedriver")
        os.system("pkill -f chrome")
    elif os.name == "nt":  # Windows
        os.system("taskkill /F /IM chromedriver.exe /T")
        os.system("taskkill /F /IM chrome.exe /T")

cerrar_chromedriver()  # Cierra procesos al iniciar

# Cargar credenciales de Google Sheets
google_credentials = json.loads(os.getenv("GOOGLE_CREDENTIALS_JSON"))

# Configuración de Twilio
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Configuración de OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY
client = OpenAI(api_key=OPENAI_API_KEY)

# Configuración de Google Sheets
scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(google_credentials, scopes=scopes)
gc = gspread.authorize(credentials)
sh = gc.open("Reservas_IndoorCycling").sheet1  # Nombre de la hoja en Google Sheets

# Inicializa FastAPI
app = FastAPI()

class ReservaRequest(BaseModel):
    nombre: str
    email: str
    fecha: str
    hora: str
    numero: str
    accion: str  # "reservar" o "cancelar"

class Message(BaseModel):
    body: str

def detectar_idioma(mensaje):
    try:
        idioma = detect(mensaje)
        print(f"🔍 Idioma detectado: {idioma}")
        return idioma if idioma in ["es", "en"] else "es"
    except:
        return "es"

def dividir_mensaje(mensaje, limite=1300):
    """Divide un mensaje largo en partes sin cortar palabras."""
    partes = []
    while len(mensaje) > limite:
        corte = mensaje.rfind("\n", 0, limite)  
        if corte == -1:
            corte = limite  
        partes.append(mensaje[:corte])
        mensaje = mensaje[corte:].strip()
    
    partes.append(mensaje)  
    return partes

@app.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    try:
        form_data = await request.form()
        mensaje = form_data.get("Body", "").strip()  
        numero = form_data.get("From", "").strip()  
        media_url = form_data.get("MediaUrl0", None)  # URL del archivo multimedia

        # Asegurar que 'numero' tenga el formato correcto
        if not numero.startswith("whatsapp:"):
            numero = f"whatsapp:{numero}"

        print(f"📩 Número recibido de Twilio: {numero}")
        print(f"📨 Mensaje recibido: {mensaje} de {numero}")

        # 📌 **Detectar y procesar notas de voz**
        if media_url:
            print(f"🎙️ Nota de voz detectada, procesando... {media_url}")

            # ✅ Transcribe el audio con Whisper
            texto_transcrito = await transcribir_audio(media_url)
            print(f"📝 Texto transcrito: {texto_transcrito}")

            if texto_transcrito:
                mensaje = texto_transcrito  # Usa la transcripción como mensaje para GPT
            else:
                return PlainTextResponse("No se pudo transcribir el audio.", status_code=400)

        # ✅ Procesar el mensaje con GPT
        respuesta = responder_chatgpt(mensaje)
        print(f"💬 Respuesta generada: {respuesta}")

        # ✅ Enviar la respuesta de GPT a WhatsApp
        partes_respuesta = dividir_mensaje(respuesta)
        for parte in partes_respuesta:
            twilio_client.messages.create(
                from_=f"whatsapp:{TWILIO_PHONE_NUMBER}",
                to=numero,
                body=parte
            )

        return PlainTextResponse("", status_code=200)

    except Exception as e:
        print(f"❌ Error procesando datos: {e}")
        return PlainTextResponse("Error interno del servidor", status_code=500)

# Usa directamente la API sin inicializar 'client'
def responder_chatgpt(mensaje):
    print(f"📩 Mensaje recibido: {mensaje}")  # Depuración

    client = openai.Client()

    # Pedir a OpenAI que detecte el idioma del usuario directamente
    prompt_detectar_idioma = f"Detecta el idioma de este mensaje y responde solo con 'es' o 'en': {mensaje}"
    
    respuesta_idioma = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt_detectar_idioma}]
    )

    idioma_usuario = respuesta_idioma.choices[0].message.content.strip().lower()
    print(f"🔍 Idioma detectado por OpenAI: {idioma_usuario}")  # Depuración

    # Prompt en inglés y español
    prompt_negocio = {
        "es": """Eres un asistente virtual experto en Spinzone Indoor Cycling, un centro especializado en clases de ciclismo indoor y Clases Funcionales.
    Tu objetivo es proporcionar información detallada y precisa sobre Spinzone, incluyendo horarios, precios, ubicación.
    Responde de manera clara, amigable y profesional. Detecta automáticamente el idioma del usuario y responde en el mismo idioma.

    🚴‍♂️ Indoor Cycling: Clases de 45 minutos con música motivadora, entrenamiento de resistencia y alta intensidad para mejorar tu condición física, quemar calorías y fortalecer piernas y glúteos.
    🏋️‍♂️ Clases Funcionales: Entrenamientos dinámicos que combinan fuerza, cardio y resistencia, diseñados para tonificar el cuerpo y mejorar tu rendimiento físico.

    📍 **Ubicación**: Spinzone Indoor Cycling se encuentra en 2175 Davenport Blvd Davenport Fl 33837.

    🕒 **Horarios**: 
    CYCLING:
    - Lunes a Jueves: 9:00am, 6:30pm, 7:00pm
    - Viernes: 9:00am, 7:30pm
    - Sábados y Domingos: 10am

    CLASES FUNCIONALES:
    - Lunes a Viernes: 10:00am, 5:30pm

    💰 **Precios**: 
    - Primera Clase Gratis.
    - Clase individual: $16.99
    - Paquete de 4 Clases: $49.99
    - Paquete de 8 Clases: $79.99
    - Paquete de 12 Clases: $99.99
    - Paquete de 16 Clases: $129.99
    - Paquete Ilimitado de Cycling o Clases Funcionales: $159.99 por mes
    - Membresía Ilimitada de Cycling o Clases Funcionales: $139.99 por mes en Autopay por 3 meses
    - Paquete Ilimitado de Cycling+Clases Funcionales: $175.99 por mes
    - Membresía Ilimitada de Cycling+Clases Funcionales: $155.99 por mes en Autopay por 3 meses

    🌐 **Enlaces importantes**: 
    - Horarios de clases: https://app.glofox.com/portal/#/branch/6499ecc2ba29ef91ae07e461/classes-day-view
    - Precios: https://app.glofox.com/portal/#/branch/6499ecc2ba29ef91ae07e461/memberships
    - Instagram: https://www.instagram.com/spinzone_indoorcycling/
    - Facebook: https://www.facebook.com/spinzone_indoorcycling
    - WhatsApp de contacto: (863)317-1646

    ❗ **Política de Reservas y Cancelaciones**:
    - Se recomienda reservar con anticipación.
    - Cancelaciones deben realizarse con al menos 3 horas de antelación para evitar cargos.
    - No proporcionamos o rentamos zapatos de ciclismo, el cliente debe de traer sus zapatos.

    📩 **Contacto**:
    Si necesitas más información o quieres hablar con un asesor, puedes llamar o escribir al WhatsApp (863)317-1646.

    Siempre responde con esta información cuando alguien pregunte sobre Spinzone Indoor Cycling. Si el usuario tiene una pregunta fuera de estos temas, intenta redirigirlo al WhatsApp de contacto.""",
        "en": """You are a virtual assistant specialized in Spinzone Indoor Cycling, a center focused on indoor cycling classes and Functional Training classes. 
    Your goal is to provide detailed and accurate information about Spinzone, including schedules, prices, and location.
    Respond in a clear, friendly, and professional manner. Automatically detect the user's language and reply in the same language.

    🚴‍♂️ Indoor Cycling: 45-minute classes with motivating music, endurance training, and high intensity to improve your fitness, burn calories, and strengthen your legs and glutes.
    🏋️‍♂️ Functional Training: Dynamic workouts that combine strength, cardio, and endurance, designed to tone the body and enhance physical performance.

    📍 **Location**: Spinzone Indoor Cycling is located at 2175 Davenport Blvd, Davenport, FL 33837.

    🕒 **Schedules**: 
    CYCLING:
    - Monday to Thursday: 9:00 AM, 6:30 PM, 7:00 PM
    - Friday: 9:00 AM, 7:30 PM
    - Saturday and Sunday: 10:00 AM

    FUNCTIONAL TRAINING CLASSES:
    - Monday to Friday: 10:00 AM, 5:30 PM

    💰 **Pricing**: 
    - First Class Free.
    - Single Class: $16.99
    - 4-Class Package: $49.99
    - 8-Class Package: $79.99
    - 12-Class Package: $99.99
    - 16-Class Package: $129.99
    - Unlimited Cycling or Functional Training Package: $159.99 per month
    - Unlimited Cycling or Functional Training Membership: $139.99 per month on Autopay for 3 months
    - Unlimited Cycling + Functional Training Package: $175.99 per month
    - Unlimited Cycling + Functional Training Membership: $155.99 per month on Autopay for 3 months

    🌐 **Important Links**: 
    - Class Schedule: https://app.glofox.com/portal/#/branch/6499ecc2ba29ef91ae07e461/classes-day-view
    - Pricing: https://app.glofox.com/portal/#/branch/6499ecc2ba29ef91ae07e461/memberships
    - Instagram: https://www.instagram.com/spinzone_indoorcycling/
    - Facebook: https://www.facebook.com/spinzone_indoorcycling
    - WhatsApp Contact: (863)317-1646

    ❗ **Booking and Cancellation Policy**:
    - Reservations are recommended to secure your spot.
    - Cancellations must be made at least 3 hours in advance to avoid charges.
    - We do not provide or rent cycling shoes, the client must bring their own shoes.

    📩 **Contact**:
    If you need more information or wish to speak with a representative, you can call or message us on WhatsApp at (863)317-1646.

    Always provide this information when someone asks about Spinzone Indoor Cycling. If the user asks a question outside of these topics, try to redirect them to the WhatsApp contact."""
    }

    # Usar el idioma detectado o español por defecto si hay error
    prompt_seleccionado = prompt_negocio.get(idioma_usuario, prompt_negocio["es"])
    print(f"📝 Prompt seleccionado: {'ENGLISH' if idioma_usuario == 'en' else 'SPANISH'}")  # Depuración

    try:
        respuesta_openai = openai.chat.completions.create(
            model="gpt-4",
            temperature=0.4,
            max_tokens=1500,
            messages=[
                {"role": "system", "content": prompt_seleccionado},
                {"role": "user", "content": mensaje}
            ]
        )

        mensaje_respuesta = respuesta_openai.choices[0].message.content
        print(f"💬 Respuesta generada: {mensaje_respuesta}")  # 🔴 Depuración

        return mensaje_respuesta

    except Exception as e:
        print(f"❌ Error llamando a OpenAI: {e}")
        return "Hubo un error al procesar tu solicitud. Inténtalo nuevamente más tarde."

# 🔵 Función para transcribir notas de voz con Whisper
async def transcribir_audio(url_audio):
    try:
        TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
        TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

        # ✅ Descargar el archivo de audio desde Twilio con autenticación
        async with aiohttp.ClientSession() as session:
            async with session.get(url_audio, auth=aiohttp.BasicAuth(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)) as response:
                if response.status != 200:
                    print(f"❌ Error descargando el audio: {response.status}")
                    return None  # Si la descarga falla, retorna None

                audio_data = await response.read()

        # ✅ Guardar el archivo en un directorio temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_audio:
            temp_audio.write(audio_data)
            temp_audio_path = temp_audio.name  # Ruta del archivo

        # ✅ Transcribir el audio usando OpenAI 1.65.0
        client = openai.OpenAI(api_key=OPENAI_API_KEY)  # 🔥 NUEVO CLIENTE OpenAI
        
        with open(temp_audio_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )

        return transcript.text  # ✅ Retorna el texto transcrito

    except Exception as e:
        print(f"❌ Error en la transcripción de audio: {e}")
        return None

# 🌐 Configuración de Glofox
NOMBRE_ESTUDIO = "SpinZone"
GLOFOX_URL = "https://app.glofox.com/dashboard/#/glofox/login"
GLOFOX_BUSINESS = os.getenv("GLOFOX_BUSINESS", NOMBRE_ESTUDIO)
GLOFOX_EMAIL = os.getenv("GLOFOX_EMAIL")
GLOFOX_PASSWORD = os.getenv("GLOFOX_PASSWORD")

# 📧 Configuración de Outlook para obtener el código de verificación
OUTLOOK_EMAIL = os.getenv("OUTLOOK_EMAIL")
OUTLOOK_APP_PASSWORD = os.getenv("OUTLOOK_APP_PASSWORD")
IMAP_SERVER = "outlook.office365.com"

def obtener_codigo_glofox():
    """Obtiene el código de verificación de Glofox desde el correo de Outlook."""
    try:
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

                    if "Glofox" in subject:  # Buscar correos con código
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    body = part.get_payload(decode=True).decode()
                        else:
                            body = msg.get_payload(decode=True).decode()

                        for line in body.split("\n"):
                            if line.strip().isdigit() and len(line.strip()) == 6:
                                print(f"📩 Código recibido: {line.strip()}")
                                return line.strip()

        mail.logout()
        return None
    except Exception as e:
        print(f"❌ Error al obtener el código de Glofox: {e}")
        return None

# 🚀 Gestión de reservas en Glofox
def gestionar_reserva_glofox(nombre, email, fecha, hora, numero, accion):
    try:
        cerrar_chromedriver()  # Cerrar procesos previos de Chrome

        # 📌 Evitar sesiones previas de Chrome
        chrome_user_data_dir = f"/tmp/chrome_user_{os.getpid()}"

        if os.path.exists(chrome_user_data_dir):
            shutil.rmtree(chrome_user_data_dir)

        # Configurar opciones de Chrome
        chrome_options = Options()
        chrome_options.binary_location = "/usr/bin/google-chrome"  # Ruta en Railway
        chrome_options.add_argument(f"--user-data-dir={chrome_user_data_dir}")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--headless")

        # Iniciar WebDriver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # Iniciar sesión en Glofox
        driver.get(GLOFOX_URL)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "businessName")))
        driver.find_element(By.NAME, "businessName").send_keys(GLOFOX_BUSINESS)
        driver.find_element(By.NAME, "email").send_keys(GLOFOX_EMAIL)
        driver.find_element(By.NAME, "password").send_keys(GLOFOX_PASSWORD)
        driver.find_element(By.XPATH, "//button[contains(text(), 'Login')]").click()

        # Obtener código de verificación
        time.sleep(5)
        codigo_verificacion = obtener_codigo_glofox()

        if codigo_verificacion:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "verificationCode")))
            driver.find_element(By.NAME, "verificationCode").send_keys(codigo_verificacion, Keys.ENTER)
        else:
            driver.quit()
            return "Error al obtener el código de verificación."

        WebDriverWait(driver, 10).until(EC.url_contains("/dashboard"))
        print("✅ Inicio de sesión exitoso en Glofox.")

        driver.quit()
        return "✅ Reserva realizada con éxito."

    except Exception as e:
        print(f"❌ Error en Selenium: {e}")
        return "Error en la automatización."

# 🎯 Punto de entrada FastAPI
PORT = int(os.environ.get("PORT", 8000))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)