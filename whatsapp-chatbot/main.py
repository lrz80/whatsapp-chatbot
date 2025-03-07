import uvicorn
import os
from fastapi import FastAPI, Request, Form
import openai
import requests
from twilio.twiml.messaging_response import MessagingResponse
from fastapi.responses import Response
from fastapi import FastAPI
from pydantic import BaseModel
import json
from fastapi import FastAPI, Request
from thefuzz import process
from twilio.rest import Client
from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse
from starlette.responses import PlainTextResponse
from fastapi.responses import PlainTextResponse
from langdetect import detect

def es_similar(frase_usuario, opciones, umbral=70):
    """Compara el mensaje del usuario con una lista de opciones y devuelve True si es similar."""
    mejor_coincidencia, score = process.extractOne(frase_usuario, opciones)
    return mejor_coincidencia if score >= umbral else None

def detectar_idioma(mensaje):
    try:
        idioma = detect(mensaje)
        print(f"🔍 Idioma detectado: {idioma}")  # 🔴 Agregamos este log
        return idioma
    except:
        return "es"  # Si hay error, usa español por defecto

def dividir_mensaje(mensaje, limite=1300):
    """Divide un mensaje largo en partes más pequeñas sin cortar palabras."""
    partes = []
    while len(mensaje) > limite:
        corte = mensaje[:limite].rfind(" ")  # Buscar espacio antes del límite
        if corte == -1:
            corte = limite  # Si no hay espacio, cortar en el límite exacto
        partes.append(mensaje[:corte])
        mensaje = mensaje[corte:].strip()
    partes.append(mensaje)  # Agregar la última parte
    return partes

async def transcribir_audio(audio_url: str) -> str:
    """ Descarga un audio desde la URL y lo transcribe con Whisper """
    try:
        response = requests.get(audio_url)
        if response.status_code != 200:
            return "❌ Error al descargar el audio."

        with open("audio.ogg", "wb") as f:
            f.write(response.content)

        client = openai.Client()  # Crea un cliente OpenAI

        with open("audio.ogg", "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )

        return transcript.text  # Accede correctamente al texto transcrito

    except Exception as e:
        print(f"❌ Error en la transcripción: {e}")
        return "No pude entender el audio. Intenta de nuevo."

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

class Message(BaseModel):
    body: str

# 🟢 Webhook de WhatsApp
@app.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    try:
        form_data = await request.form()  # Leer los datos del formulario
        mensaje = form_data.get("Body", "").strip()  # Extraer el mensaje de texto
        numero = form_data.get("From", "").strip()  # Extraer el número del usuario
        audio_url = form_data.get("MediaUrl0")  # URL del audio si es una nota de voz

        if audio_url:
            print(f"🎙️ Nota de voz recibida: {audio_url}")  # Log de la nota de voz
            texto_transcrito = await transcribir_audio(audio_url)  # Llamar a la función

            # Enviar la transcripción a ChatGPT para obtener una respuesta
            respuesta = responder_chatgpt(texto_transcrito)
            return PlainTextResponse(respuesta, status_code=200)

        if not mensaje:
            return PlainTextResponse("Mensaje vacío", status_code=400)

        # Procesar mensaje de texto normalmente con ChatGPT
        respuesta = responder_chatgpt(mensaje)
        return PlainTextResponse(respuesta, status_code=200)

    except Exception as e:
        print(f"❌ Error procesando datos: {e}")
        return PlainTextResponse("Error interno del servidor", status_code=500)

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

    # PROMPTS en ambos idiomas
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

    📩 **Contact**:
    If you need more information or wish to speak with a representative, you can call or message us on WhatsApp at (863)317-1646.

    Always provide this information when someone asks about Spinzone Indoor Cycling. If the user asks a question outside of these topics, try to redirect them to the WhatsApp contact."""
}

    # Usar el idioma detectado o español por defecto si hay error
    prompt_seleccionado = prompt_negocio.get(idioma_usuario, prompt_negocio["es"])
    print(f"📝 Prompt seleccionado: {'ENGLISH' if idioma_usuario == 'en' else 'SPANISH'}")  # Depuración

    # 🔹 Definir palabras clave con fuzzy matching
    opciones_horario = ["horario", "horarios", "qué horario tienen?", "dime los horarios"]
    opciones_precios = ["precios", "cuánto cuesta", "planes", "tarifas", "costos"]
    opciones_info = ["información", "quiero información", "dame más información", "cuéntame sobre spinzone"]

    mensaje_clave = mensaje  # 🔹 Asegurar que siempre tenga un valor

    if es_similar(mensaje.lower(), opciones_horario):
        mensaje_clave = "Dime los horarios de Spinzone Indoor Cycling."
    elif es_similar(mensaje.lower(), opciones_precios):
        mensaje_clave = "Dime los precios de Spinzone Indoor Cycling."
    elif es_similar(mensaje.lower(), opciones_info):
        mensaje_clave = "Dame información general sobre Spinzone Indoor Cycling."

    print(f"Mensaje clave: {mensaje_clave}")  # 🔹 Depuración

    respuesta = client.chat.completions.create(
        model="gpt-4",
        temperature=0.4,
        max_tokens=1500,
        messages=[
            {"role": "system", "content": prompt_seleccionado},
            {"role": "user", "content": mensaje}
        ]
    )

    # Obtener la respuesta del asistente
    mensaje_respuesta = respuesta.choices[0].message.content
    print(f"💬 Respuesta generada: {mensaje_respuesta}")  # 🔴 Depuración

    return mensaje_respuesta

def analizar_imagen(url_imagen):
    client = openai.Client()
    respuesta = client.chat.completions.create(
        model="gpt-4-vision-preview",
        messages=[
            {"role": "system", "content": "Describe la imagen en detalle."},
            {"role": "user", "content": {"image": url_imagen}}
        ]
    )

    return respuesta.choices[0].message.content

# 🔵 Función para procesar imágenes con GPT-4 Vision
def analizar_imagen(url_imagen):
    respuesta = openai.ChatCompletion.create(
        model="gpt-4-vision-preview",
        messages=[
            {"role": "system", "content": "Describe la imagen de forma detallada."},
            {"role": "user", "content": {"image": url_imagen}}
        ]
    )
    return respuesta["choices"][0]["message"]["content"]

# 🔴 Función para transcribir notas de voz con Whisper
@app.post("/transcribir_audio")
async def transcribir_audio(url_audio: str):
    audio_data = requests.get(url_audio).content
    with open("audio.ogg", "wb") as f:
        f.write(audio_data)

    audio_file = open("audio.ogg", "rb")
    transcript = openai.Audio.transcribe("whisper-1", audio_file)
    
    return {"texto_transcrito": transcript["text"]}

# Obtener el puerto desde las variables de entorno de Railway
PORT = int(os.environ.get("PORT", 8000))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)