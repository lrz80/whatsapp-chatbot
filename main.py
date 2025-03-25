import uvicorn
import os
from fastapi import FastAPI, Request
import openai
from openai import OpenAI
import requests
from twilio.rest import Client
from langdetect import detect
from dotenv import load_dotenv
import aiohttp
import tempfile

# Cargar variables de entorno
load_dotenv()

# Configuración de Twilio
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Configuración de OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# Inicializa FastAPI
app = FastAPI()

def detectar_idioma(mensaje):
    try:
        idioma = detect(mensaje)
        print(f"🔍 Idioma detectado: {idioma}")
        return idioma if idioma in ["es", "en"] else "es"
    except:
        return "es"

def dividir_mensaje(mensaje, limite=1000):
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

        if not numero.startswith("whatsapp:"):
            numero = f"whatsapp:{numero}"

        print(f"📨 Mensaje recibido: {mensaje} de {numero}")

        respuesta = responder_chatgpt(mensaje)
        print(f"💬 Respuesta generada: {respuesta}")

        partes_respuesta = dividir_mensaje(respuesta)
        for parte in partes_respuesta:
            twilio_client.messages.create(
                from_=f"whatsapp:{TWILIO_PHONE_NUMBER}",
                to=numero,
                body=parte
            )

        return {"status": "success"}

    except Exception as e:
        print(f"❌ Error procesando datos: {e}")
        return {"status": "error", "message": str(e)}

# 🚀 **Nueva Función de OpenAI con Respuestas Más Inteligentes**
def responder_chatgpt(mensaje):
    print(f"📩 Mensaje recibido: {mensaje}")

    idioma_usuario = detectar_idioma(mensaje)

    prompt_negocio = {
        "es": """
        Responde como asistente virtual de Spinzone Indoor Cycling. Da respuestas claras, directas y profesionales.
        Evita mensajes genéricos y solo proporciona información relevante según la pregunta del usuario.

        📍 **Ubicación**: Spinzone Indoor Cycling - 2175 Davenport Blvd Davenport Fl 33837.
        🕒 **Horarios**:
        CYCLING:
        - Lunes - Martes - Jueves: 9:00am, 6:30pm, 7:30pm
        - Miercoles: 8:00am, 9:00am, 6:30pm, 7:30pm
        - Viernes: 9:00am, 7:30pm
        - Sábados y Domingos: 10am
        CLASES FUNCIONALES:
        - Lunes a Jueves: 10:00am, 5:30pm
        - Viernes: 10:00am, 6:30pm
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
        📲 **WhatsApp**: (863)317-1646
        🌐 **Enlaces**:
        - Reservas: https://app.glofox.com/portal/#/branch/6499ecc2ba29ef91ae07e461/classes-day-view
        - Precios: https://app.glofox.com/portal/#/branch/6499ecc2ba29ef91ae07e461/memberships
        - Para obtener la Clase Gratis: https://app.glofox.com/portal/#/branch/6499ecc2ba29ef91ae07e461/memberships/64bd9335561ca2443a00eb16/plan/1690145417424/buy
        ❗ **Política**:
        - Reservas recomendadas, cancelaciones con 3h de antelación, No proporcionamos o rentamos zapatos de ciclismo, el cliente debe de traer sus zapatos.
        """,
        "en": """
        Act as Spinzone Indoor Cycling’s virtual assistant. Provide clear, direct, and professional responses.
        Avoid generic messages and only provide relevant information based on the user's query.

        📍 **Location**: Spinzone Indoor Cycling - 2175 Davenport Blvd, Davenport, FL 33837.
        🕒 **Hours**:
        CYCLING:
        - Monday - Tuesday - Thursday: 9:00 AM, 6:30 PM, 7:30 PM
        - Wednesday: 8:00am, 9:00am, 6:30pm, 7:30pm
        - Friday: 9:00 AM, 7:30 PM
        - Saturday and Sunday: 10:00 AM
        FUNCTIONAL TRAINING CLASSES:
        - Monday to Thursday: 10:00 AM, 5:30 PM
        - Friday: 10:00am, 6:30pm
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
        📲 **WhatsApp**: (863)317-1646
        🌐 **Links**:
        - Booking: https://app.glofox.com/portal/#/branch/6499ecc2ba29ef91ae07e461/classes-day-view
        - Pricing: https://app.glofox.com/portal/#/branch/6499ecc2ba29ef91ae07e461/memberships
        - To get the Free Class: https://app.glofox.com/portal/#/branch/6499ecc2ba29ef91ae07e461/memberships/64bd9335561ca2443a00eb16/plan/1690145417424/buy
        ❗ **Policy**:
        - Booking recommended, cancellations 3h in advance, We do not provide or rent cycling shoes, the client must bring their own shoes.
        """
    }

    prompt_seleccionado = prompt_negocio.get(idioma_usuario, prompt_negocio["es"])

    try:
        respuesta_openai = openai.chat.completions.create(
            model="gpt-4",
            temperature=0.3,  # 🔥 Respuestas más directas y menos creativas
            max_tokens=800,  # ⬇️ Reducido para evitar errores de Twilio
            messages=[
                {"role": "system", "content": prompt_seleccionado},
                {"role": "user", "content": mensaje}
            ]
        )

        mensaje_respuesta = respuesta_openai.choices[0].message.content.strip()
        print(f"💬 Respuesta generada: {mensaje_respuesta}")

        return mensaje_respuesta

    except Exception as e:
        print(f"❌ Error llamando a OpenAI: {e}")
        return "Hubo un error al procesar tu solicitud. Inténtalo nuevamente más tarde."

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
