import uvicorn
import os
import imaplib
import email
import re
import time
import gspread
import asyncio
import aiohttp
import tempfile
import openai
import uuid
import shutil
import requests
import platform
from time import sleep
from fastapi import FastAPI, Request
from fastapi import FastAPI, Request, Form
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from twilio.rest import Client
from langdetect import detect
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import json
from google.oauth2.service_account import Credentials
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from email.header import decode_header
from selenium.webdriver.common.keys import Keys
from openai import OpenAI
from twilio.twiml.messaging_response import MessagingResponse
from email_helper import obtener_codigo_glofox
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.webdriver import RemoteConnection

# Cargar variables de entorno
load_dotenv()

# Inicializa FastAPI
app = FastAPI()

# 🔹 **Función para iniciar WebDriver correctamente**
def iniciar_webdriver():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

# Verificar si se cargaron correctamente
print("GLOFOX_BUSINESS:", os.getenv("GLOFOX_BUSINESS"))
print("GLOFOX_EMAIL:", os.getenv("GLOFOX_EMAIL"))
print("GLOFOX_PASSWORD:", os.getenv("GLOFOX_PASSWORD"))

# Función para cerrar sesiones previas de ChromeDriver antes de iniciar
def cerrar_chromedriver():
    sistema = platform.system()
    
    if sistema == "Linux" or sistema == "Darwin":  # Darwin es para Mac
        os.system("pkill -f chromedriver")  
        os.system("pkill -f chrome")  
    elif sistema == "Windows":
        os.system("taskkill /F /IM chromedriver.exe /T")  
        os.system("taskkill /F /IM chrome.exe /T")  

cerrar_chromedriver()  # Llamar antes de iniciar una nueva sesión

# 📌 Cargar credenciales de Google Sheets
google_credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
if not google_credentials_json:
    raise ValueError("⚠️ ERROR: No se encontró GOOGLE_CREDENTIALS_JSON en las variables de entorno.")

google_credentials = json.loads(google_credentials_json)

scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(google_credentials, scopes=scopes)
gc = gspread.authorize(credentials)
sh = gc.open("Reservas_IndoorCycling").sheet1


# 📌 Configuración de Twilio
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# 📌 Configuración de OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# Verificar que se cargaron correctamente
print("🔑 OPENAI_API_KEY:", "Cargada correctamente" if OPENAI_API_KEY else "❌ No encontrada")
print("📞 TWILIO_ACCOUNT_SID:", "Cargada correctamente" if TWILIO_ACCOUNT_SID else "❌ No encontrada")
print("🔑 TWILIO_AUTH_TOKEN:", "Cargada correctamente" if TWILIO_AUTH_TOKEN else "❌ No encontrada")

# 📌 Clase para manejar reservas
class ReservaRequest(BaseModel):
    nombre: str
    email: str
    fecha: str
    hora: str
    numero: str
    accion: str  # "reservar" o "cancelar"

# 📌 Webhook de WhatsApp
@app.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    try:
        form_data = await request.form()
        mensaje = form_data.get("Body", "").strip().lower()
        numero = form_data.get("From", "").strip()

        if not numero.startswith("whatsapp:"):
            numero = f"whatsapp:{numero}"

        print(f"📨 Mensaje recibido en WhatsApp: {mensaje} de {numero}")

        if any(palabra in mensaje for palabra in ["reservar", "agendar"]):
            print("✅ Se detectó un intento de reserva en WhatsApp")

            partes = mensaje.split()
            if len(partes) < 6:
                return PlainTextResponse("", status_code=200)

            nombre = partes[1] + " " + partes[2]
            email = partes[3]
            fecha = partes[4]
            hora = partes[5]

            resultado = gestionar_reserva_glofox(nombre, email, fecha, hora, numero, "reservar")

            twilio_client.messages.create(
                from_=f"whatsapp:{TWILIO_PHONE_NUMBER}",
                to=numero,
                body=resultado
            )
            return PlainTextResponse("", status_code=200)

        elif "cancelar" in mensaje:
            partes = mensaje.split()
            if len(partes) < 6:
                return PlainTextResponse("", status_code=200)

            nombre = partes[1] + " " + partes[2]
            email = partes[3]
            fecha = partes[4]
            hora = partes[5]

            resultado = gestionar_reserva_glofox(nombre, email, fecha, hora, numero, "cancelar")

            twilio_client.messages.create(
                from_=f"whatsapp:{TWILIO_PHONE_NUMBER}",
                to=numero,
                body=resultado
            )
            return PlainTextResponse("", status_code=200)

        else:
            respuesta = responder_chatgpt(mensaje)

            twilio_client.messages.create(
                from_=f"whatsapp:{TWILIO_PHONE_NUMBER}",
                to=numero,
                body=respuesta
            )
            return PlainTextResponse("", status_code=200)

    except Exception as e:
        print(f"❌ Error procesando mensaje de WhatsApp: {e}")
        return PlainTextResponse("Error interno del servidor", status_code=500)
    
# Usa directamente la API sin inicializar 'client'
def responder_chatgpt(mensaje):
    print(f"📩 Mensaje recibido: {mensaje}")

    try:
        client = OpenAI(api_key=OPENAI_API_KEY)

        prompt_detectar_idioma = f"Detecta el idioma de este mensaje y responde solo con 'es' o 'en': {mensaje}"

        respuesta_idioma = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt_detectar_idioma}]
        )

        idioma_usuario = respuesta_idioma.choices[0].message.content.strip().lower()
        print(f"🔍 Idioma detectado: {idioma_usuario}")

        # 🔴 **Aquí definimos `prompt_negocio` dentro de la función**
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

        prompt_seleccionado = prompt_negocio.get(idioma_usuario, prompt_negocio["es"])

        respuesta_openai = client.chat.completions.create(
            model="gpt-4",
            temperature=0.4,
            max_tokens=1100,
            messages=[
                {"role": "system", "content": prompt_seleccionado},
                {"role": "user", "content": mensaje}
            ]
        )

        mensaje_respuesta = respuesta_openai.choices[0].message.content
        print(f"💬 Respuesta generada: {mensaje_respuesta}")

        return mensaje_respuesta

    except Exception as e:
        print(f"❌ Error llamando a OpenAI: {e}")
        return "❌ Error en la IA, intenta más tarde."


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

def obtener_codigo_glofox():
    print("📩 Buscando código de verificación en Outlook...")

    # Conectar con la cuenta de Outlook (IMAP)
    EMAIL = os.getenv("GLOFOX_EMAIL")
    PASSWORD = os.getenv("GLOFOX_PASSWORD")

    try:
        mail = imaplib.IMAP4_SSL("outlook.office365.com")
        mail.login(EMAIL, PASSWORD)
        mail.select("inbox")

        # Buscar correos con el asunto relacionado con Glofox
        result, data = mail.search(None, '(FROM "noreply@glofox.com")')
        mail_ids = data[0].split()

        if not mail_ids:
            print("❌ No se encontró un correo de verificación de Glofox.")
            return None

        # Leer el último correo
        latest_email_id = mail_ids[-1]
        result, data = mail.fetch(latest_email_id, "(RFC822)")
        raw_email = data[0][1]
        msg = email.message_from_bytes(raw_email)

        # Extraer el cuerpo del email
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode()
                    break
        else:
            body = msg.get_payload(decode=True).decode()

        # Buscar el código en el email (ajustar según el formato)
        import re
        match = re.search(r"Verification code: (\d{6})", body)
        if match:
            codigo = match.group(1)
            print(f"✅ Código de verificación encontrado: {codigo}")
            return codigo
        else:
            print("❌ No se encontró un código en el email.")
            return None

    except Exception as e:
        print(f"❌ Error obteniendo el código: {e}")
        return None

# 📌 Definir función para gestionar reservas en Glofox
def gestionar_reserva_glofox(nombre, email, fecha, hora, numero, accion):
    try:
        print(f"🔹 Intentando {accion} para {nombre} con email {email}, fecha {fecha}, hora {hora}, número {numero}")

        # 1️⃣ **Abrir la página de login de Glofox**
        driver.get("https://app.glofox.com/dashboard/#/glofox/login")
        print("🌐 Página de Glofox cargada.")

        # 2️⃣ **Seleccionar el negocio**
        xpath_business = "//*[@id='content-container--angular']/div/entry-branch-selection/div/div/form/entry-textbox-dropdown/div/input"

        WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, xpath_business)))
        campo_business = driver.find_element(By.XPATH, xpath_business)

        # 🔥 **Forzar clic y escritura como humano**
        campo_business.click()
        business_name = os.getenv("GLOFOX_BUSINESS", "SpinZone")  # Default en caso de que la variable de entorno esté vacía
        campo_business.clear()
        campo_business.send_keys(business_name)
        print(f"📌 Se escribió en Business Name: {business_name}")

        # 🔥 **Esperar a que aparezca la lista desplegable y seleccionar**
        try:
            lista_desplegable = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, f"//div[contains(text(), '{business_name}')]"))
            )
            time.sleep(2)  # Espera extra
            campo_business.send_keys(Keys.ARROW_DOWN)
            time.sleep(1)
            campo_business.send_keys(Keys.ENTER)
            print("✅ Se seleccionó el negocio correctamente.")
        except Exception as e:
            print(f"⚠️ No se pudo seleccionar el negocio: {e}")

        # 🔥 **Hacer clic fuera del campo para "confirmar" la selección**
        driver.find_element(By.TAG_NAME, "body").click()
        time.sleep(2)  # Espera extra para asegurar la selección

        print("🔹 Negocio seleccionado, avanzando al email...")

        # 3️⃣ **Esperar y encontrar el campo de email**
        try:
            # Esperar a que el campo de email esté visible
            campo_email = WebDriverWait(driver, 15).until(
                EC.visibility_of_element_located((By.XPATH, "//input[contains(@placeholder, 'Enter your email address')]"))
            )
            email = os.getenv("GLOFOX_EMAIL")
            print("✅ Campo de email encontrado:", campo_email)
        except Exception as e:
            print("❌ ERROR: No se encontró el campo de email. Detalles:", str(e))

        # ✅ **Forzar visibilidad del campo (por si está oculto o deshabilitado)**
        driver.execute_script("""
            let campo = arguments[0];
            campo.removeAttribute('disabled');
            campo.removeAttribute('readonly');
            campo.style.display = 'block';
            campo.style.visibility = 'visible';
            campo.style.opacity = '1';
            campo.focus();
        """, campo_email)

        # Intentar con send_keys()
        campo_email.click()
        campo_email.clear()
        campo_email.send_keys("GLOFOX_EMAIL")

        # Verificar si se ingresó correctamente
        email_ingresado = driver.execute_script("return arguments[0].value;", campo_email)
        if email_ingresado != "GLOFOX_EMAIL":
            print("⚠️ Intentando con JavaScript...")
            driver.execute_script("arguments[0].value = arguments[1];", campo_email, "GLOFOX_EMAIL")
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", campo_email)

        print("✅ Email ingresado correctamente.")

        # 4️⃣ **Ingresar Contraseña**
        xpath_password = "//*[@id='content-container--angular']/div/entry-branch-selection/div/div/form/div[2]/input"
        WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, xpath_password)))
        campo_password = driver.find_element(By.XPATH, xpath_password)
        campo_password.click()
        escribir_como_humano(campo_password, os.getenv("GLOFOX_PASSWORD"), retraso=0.2)
        print("✅ Contraseña ingresada correctamente.")

        # 5️⃣ **Clic en el botón de Login**
        xpath_boton_login = "//*[@id='content-container--angular']/div/entry-branch-selection/div/div/form/div[3]/button"
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, xpath_boton_login)))
        boton_login = driver.find_element(By.XPATH, xpath_boton_login)
        boton_login.click()
        print("✅ Se hizo clic en Login.")

        # 6️⃣ **Esperar código de verificación y escribirlo**
        time.sleep(5)
        codigo_verificacion = obtener_codigo_glofox()
        if not codigo_verificacion:
            print("❌ No se pudo obtener el código de verificación.")
            return "❌ Error en la verificación."

        xpath_verificacion = "//*[@id='content-container--angular']/div/entry-verification/div/div/form/div[1]/input"
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.XPATH, xpath_verificacion)))
        campo_verificacion = driver.find_element(By.XPATH, xpath_verificacion)
        campo_verificacion.send_keys(codigo_verificacion, Keys.ENTER)
        print("✅ Código ingresado correctamente.")

        # 7️⃣ **Reservar la clase**
        driver.get("https://app.glofox.com/portal/#/branch/6499ecc2ba29ef91ae07e461/classes-day-view")
        time.sleep(3)

        driver.find_element(By.XPATH, "//input[@name='date']").send_keys(fecha)
        driver.find_element(By.XPATH, "//input[@name='time']").send_keys(hora)
        driver.find_element(By.XPATH, "//input[@name='name']").send_keys(nombre)
        driver.find_element(By.XPATH, "//input[@name='email']").send_keys(email)
        driver.find_element(By.XPATH, "//input[@name='phone']").send_keys(numero)

        try:
            boton_reserva = driver.find_element(By.XPATH, "//button[contains(text(), 'Reservar')]")
            boton_reserva.click()
            print("✅ Reserva realizada correctamente.")
        except Exception as e:
            print(f"❌ No se pudo hacer clic en el botón de reserva: {e}")
            return "❌ Error al intentar reservar la clase."

        time.sleep(3)
        driver.quit()

        return f"✅ ¡Hola {nombre}! Tu clase de Indoor Cycling está confirmada para el {fecha} a las {hora}. 🚴‍♂️🔥"

    except Exception as e:
        print(f"❌ Error en Selenium: {e}")
        return f"❌ Error en Selenium: {str(e)}"

# 📌 Ejecutar FastAPI
PORT = int(os.environ.get("PORT", 8000))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
