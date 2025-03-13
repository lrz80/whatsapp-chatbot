import uvicorn
import os
import time
import gspread
import asyncio
import aiohttp
import tempfile
import openai
import undetected_chromedriver as uc
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
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import json
from oauth2client.service_account import ServiceAccountCredentials
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Cargar variables de entorno
load_dotenv()

# Cargar credenciales desde una variable de entorno en lugar de un archivo
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

# Configurar acceso a Google Sheets
credentials = ServiceAccountCredentials.from_json_keyfile_dict(google_credentials, ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
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

# Función para detectar idioma
def detectar_idioma(mensaje):
    try:
        idioma = detect(mensaje)
        return idioma if idioma in ["es", "en"] else "es"
    except:
        return "es"

# Función para manejar reservas/cancelaciones en Glofox
def gestionar_reserva_glofox(nombre, email, fecha, hora, numero, accion):
    try:
        print("🔹 Configurando Selenium con Chrome en Railway...")

        chrome_options = Options()
        chrome_options.binary_location = "/usr/bin/google-chrome"  # Ruta de Chrome en Railway
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        # Ruta corregida de ChromeDriver en Railway
        service = Service("/usr/local/bin/chromedriver")  
        driver = webdriver.Chrome(service=service, options=chrome_options)

        print("✅ Selenium configurado correctamente.")

        driver.get("https://app.glofox.com/portal/#/login")
        print("🔹 Iniciando sesión en Glofox...")

        driver.find_element("id", "email").send_keys("tu_email@example.com")
        driver.find_element("id", "password").send_keys("tu_contraseña")
        driver.find_element("id", "login-button").click()
        time.sleep(3)

        if accion == "reservar":
            print(f"🔹 Buscando la clase para {fecha} a las {hora}...")
            driver.get("https://app.glofox.com/portal/#/branch/6499ecc2ba29ef91ae07e461/classes-day-view")
            time.sleep(2)

            try:
                boton_clase = driver.find_element("xpath", "//button[contains(text(), 'Indoor Cycling')]")
                boton_clase.click()
                print("✅ Clase encontrada y seleccionada.")
            except Exception as e:
                print(f"❌ No se encontró el botón de la clase: {e}")
                driver.quit()
                return "No se pudo encontrar la clase en Glofox."

            driver.find_element("xpath", "//input[@name='date']").send_keys(fecha)
            driver.find_element("xpath", "//input[@name='time']").send_keys(hora)
            driver.find_element("xpath", "//input[@name='name']").send_keys(nombre)
            driver.find_element("xpath", "//input[@name='email']").send_keys(email)
            driver.find_element("xpath", "//input[@name='phone']").send_keys(numero)

            try:
                boton_reserva = driver.find_element("xpath", "//button[contains(text(), 'Reservar')]")
                boton_reserva.click()
                print("✅ Reserva realizada correctamente.")
            except Exception as e:
                print(f"❌ No se pudo hacer clic en el botón de reserva: {e}")
                driver.quit()
                return "Error al intentar reservar la clase."

            time.sleep(3)
            mensaje = f"✅ ¡Hola {nombre}! Tu clase de Indoor Cycling está confirmada para el {fecha} a las {hora}. 🚴‍♂️🔥"

        driver.quit()
        return mensaje

    except Exception as e:
        print(f"❌ Error en Selenium: {e}")
        return "Ocurrió un error en la automatización."

@app.post("/reserva")
async def recibir_reserva(request: ReservaRequest):
    resultado = gestionar_reserva_glofox(request.nombre, request.fecha, request.hora, request.numero, request.accion)
    return {"mensaje": resultado}

@app.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    try:
        form_data = await request.form()
        mensaje = form_data.get("Body", "").strip().lower()
        numero = form_data.get("From", "").strip()

        if not numero.startswith("whatsapp:"):
            numero = f"whatsapp:{numero}"

        print(f"📨 Mensaje recibido: {mensaje} de {numero}")

        # 🔍 Detectar si es una reserva
        if any(palabra in mensaje for palabra in ["reservar", "agendar", "quiero reservar", "quiero agendar"]):
            partes = mensaje.split()

            if len(partes) < 6:
                twilio_client.messages.create(
                    from_=f"whatsapp:{TWILIO_PHONE_NUMBER}",
                    to=numero,
                    body="📅 Para reservar, envía: 'Reservar Nombre Apellido Email Fecha Hora'. Ejemplo: 'Reservar Juan Pérez juan@email.com 2024-03-25 18:00'."
                )
                return PlainTextResponse("", status_code=200)

            # Extraer datos
            nombre = partes[1] + " " + partes[2]  
            email = partes[3]
            fecha = partes[4]
            hora = partes[5]

            print(f"🔹 Procesando reserva: {nombre}, {email}, {fecha}, {hora}")

            # Llamar a la función de reserva en Glofox
            resultado = gestionar_reserva_glofox(nombre, email, fecha, hora, numero, "reservar")

            # Enviar confirmación
            twilio_client.messages.create(
                from_=f"whatsapp:{TWILIO_PHONE_NUMBER}",
                to=numero,
                body=resultado
            )
            return PlainTextResponse("", status_code=200)

        # 🔍 Detectar si es una cancelación
        elif "cancelar" in mensaje:
            partes = mensaje.split()

            if len(partes) < 6:
                twilio_client.messages.create(
                    from_=f"whatsapp:{TWILIO_PHONE_NUMBER}",
                    to=numero,
                    body="🗑 Para cancelar una reserva, usa: 'Cancelar Nombre Apellido Email Fecha Hora'."
                )
                return PlainTextResponse("", status_code=200)

            nombre = partes[1] + " " + partes[2]
            email = partes[3]
            fecha = partes[4]
            hora = partes[5]

            print(f"🔹 Procesando cancelación: {nombre}, {email}, {fecha}, {hora}")

            resultado = gestionar_reserva_glofox(nombre, email, fecha, hora, numero, "cancelar")

            twilio_client.messages.create(
                from_=f"whatsapp:{TWILIO_PHONE_NUMBER}",
                to=numero,
                body=resultado
            )
            return PlainTextResponse("", status_code=200)

        # 🧠 Si no es una reserva ni cancelación, responder con OpenAI
        else:
            idioma_usuario = detectar_idioma(mensaje)
            prompt_seleccionado = prompt_negocio.get(idioma_usuario, prompt_negocio["es"])

            respuesta = client.chat.completions.create(
                model="gpt-4",
                temperature=0.4,
                max_tokens=1500,
                messages=[{"role": "system", "content": prompt_seleccionado}, {"role": "user", "content": mensaje}]
            )

            respuesta_texto = respuesta.choices[0].message.content

            twilio_client.messages.create(
                from_=f"whatsapp:{TWILIO_PHONE_NUMBER}",
                to=numero,
                body=respuesta_texto
            )
            return PlainTextResponse("", status_code=200)

    except ClientDisconnect:
        print("⚠️ Cliente desconectado antes de completar la solicitud.")
        return PlainTextResponse("Cliente desconectado.", status_code=499)

    except Exception as e:
        print(f"❌ Error en webhook de WhatsApp: {e}")
        return PlainTextResponse("Error interno del servidor", status_code=500)

PORT = int(os.environ.get("PORT", 8000))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
