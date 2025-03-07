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
        mensaje = form_data.get("Body", "").strip()  # Extraer el mensaje
        numero = form_data.get("From", "").strip()  # Número de teléfono del usuario

        if not mensaje:
            return PlainTextResponse("Mensaje vacío", status_code=400)

        print(f"📩 Mensaje recibido: {mensaje} de {numero}")

        # Llamamos a la función para procesar el mensaje con GPT
        respuesta = responder_chatgpt(mensaje)

        print(f"💬 Respuesta generada: {respuesta}")

        return PlainTextResponse(respuesta, status_code=200)  # Responder en texto plano

    except Exception as e:
        print(f"❌ Error procesando datos: {e}")
        return PlainTextResponse("Error interno del servidor", status_code=500)

def responder_chatgpt(mensaje):
    print(f"Mensaje recibido: {mensaje}")  # Depuración

    client = openai.Client()

    try:
        idioma_usuario = detect(mensaje)  # Detectamos el idioma del mensaje del usuario
        print(f"Idioma detectado: {idioma_usuario}")  # Debugging
    except:
        idioma_usuario = "es"  # Si no se puede detectar, asumir español

    prompt_negocio = "Información general sobre Spinzone Indoor Cycling."

    # 🔥 Modificamos el prompt para forzar respuesta en el mismo idioma
    prompt_modificado = f"{prompt_negocio}\n\nResponde en el idioma del usuario detectado ({idioma_usuario})."

    # 🔹 Definir el prompt del negocio
    prompt_negocio = """
    Eres un asistente virtual experto en Spinzone Indoor Cycling, un centro especializado en clases de ciclismo indoor y Clases Funcionales. 
    Tu objetivo es proporcionar información detallada y precisa sobre Spinzone, incluyendo horarios, precios, ubicación. 
    Responde de manera clara, amigable y profesional. Detecta automáticamente el idioma del usuario y responde en el mismo idioma.

    🚴‍♂️Indoor Cycling: Clases de 45 minutos con música motivadora, entrenamiento de resistencia y alta intensidad para mejorar tu condición física, quemar calorías y fortalecer piernas y glúteos.
    🏋️‍♂️Clases Funcionales: Entrenamientos dinámicos que combinan fuerza, cardio y resistencia, diseñados para tonificar el cuerpo y mejorar tu rendimiento físico.

    📍 **Ubicación**: 
    Spinzone Indoor Cycling se encuentra en 2175 Davenport Blvd Davenport Fl 33837.

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

    Siempre responde con esta información cuando alguien pregunte sobre Spinzone Indoor Cycling. Si el usuario tiene una pregunta fuera de estos temas, intenta redirigirlo al WhatsApp de contacto.
    """

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
            {"role": "system", "content": prompt_negocio},
            {"role": "user", "content": mensaje_clave}
        ]
    )

    # 🛠 Solución rápida: asegurar que la respuesta sea un string antes de enviarla
    respuesta_generada = respuesta.choices[0].message.content
    
    if isinstance(respuesta_generada, list):  # Si es lista, conviértela en string
        respuesta_generada = "\n".join(respuesta_generada)

    print(f"Respuesta generada: {respuesta_generada}")  # Debugging
    
    return respuesta_generada  # Retornamos la respuesta ya corregida

def dividir_mensaje(mensaje, limite=1300):
    """Divide un mensaje largo en partes más pequeñas sin cortar palabras."""
    partes = []
    while len(mensaje) > limite:
        corte = mensaje.rfind("\n", 0, limite)  # Busca un salto de línea antes del límite
        if corte == -1:  # Si no hay salto de línea, corta en el límite exacto
            corte = limite
        partes.append(mensaje[:corte])
        mensaje = mensaje[corte:].strip()
    partes.append(mensaje)  # Agrega la última parte
    return partes


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