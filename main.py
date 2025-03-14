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

# Cargar variables de entorno
load_dotenv()

# 📌 Instalar ChromeDriver y asegurarse de que Chrome está configurado correctamente
service = Service(ChromeDriverManager().install())

# Función para cerrar sesiones previas de ChromeDriver antes de iniciar
def cerrar_chromedriver():
    os.system("pkill -f chromedriver")  # Mata todos los procesos de ChromeDriver
    os.system("pkill -f chrome")  # Mata todos los procesos de Chrome

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

# Inicializa FastAPI
app = FastAPI()

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
            max_tokens=1500,
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

# 📌 Definir función para gestionar reservas en Glofox
def gestionar_reserva_glofox(nombre, email, fecha, hora, numero, accion):
    try:
        print(f"🔹 Intentando {accion} para {nombre} con email {email}, fecha {fecha}, hora {hora}, número {numero}")

        chrome_options = webdriver.ChromeOptions()
        chrome_user_data_dir = f"/tmp/chrome_user_{os.getpid()}"

        if os.path.exists(chrome_user_data_dir):
            try:
                shutil.rmtree(chrome_user_data_dir)
            except Exception as e:
                print(f"⚠️ Advertencia: No se pudo eliminar {chrome_user_data_dir}: {e}")

        chrome_options.add_argument(f"--user-data-dir={chrome_user_data_dir}")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--headless")  # <-- Comenta esta línea para pruebas

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        driver.get("https://app.glofox.com/dashboard/#/glofox/login")

        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "businessName")))
        driver.find_element(By.NAME, "businessName").send_keys(os.getenv("GLOFOX_BUSINESS"))
        driver.find_element(By.NAME, "email").send_keys(os.getenv("GLOFOX_EMAIL"))
        driver.find_element(By.NAME, "password").send_keys(os.getenv("GLOFOX_PASSWORD"))
        driver.find_element(By.XPATH, "//button[contains(text(), 'Login')]").click()

        time.sleep(5)

        codigo_verificacion = obtener_codigo_glofox()
        if not codigo_verificacion:
            driver.quit()
            return "❌ Error: No se pudo obtener el código de verificación."

        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "verificationCode")))
        driver.find_element(By.NAME, "verificationCode").send_keys(codigo_verificacion, Keys.ENTER)

        driver.quit()
        return f"✅ {accion.capitalize()} realizada con éxito."

    except Exception as e:
        print(f"❌ Error en Selenium: {e}")
        return "Error en la reserva, intenta de nuevo más tarde."

# 📌 Ejecutar FastAPI
PORT = int(os.environ.get("PORT", 8000))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
