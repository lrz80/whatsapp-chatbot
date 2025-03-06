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

# Configura las API Keys
OPENAI_API_KEY = "tu_openai_api_key"
TWILIO_NUMBER = "tu_numero_twilio"
TWILIO_AUTH_TOKEN = "tu_auth_token"
TWILIO_SID = "tu_twilio_sid"

# Inicializa FastAPI
app = FastAPI()

class Message(BaseModel):
    body: str

openai.api_key = OPENAI_API_KEY

# Respuestas predefinidas
RESPUESTAS_PERSONALIZADAS = {
    "horario": "Nuestro horario de atención es de 9 AM a 6 PM.",
    "precio": "Los precios varían según el producto. ¿Cuál te interesa?",
    "contacto": "Puedes llamarnos al +123456789."
}

def dividir_mensaje(mensaje, limite=1600):
    """Divide un mensaje en fragmentos de máximo 'limite' caracteres."""
    return [mensaje[i:i+limite] for i in range(0, len(mensaje), limite)]

mensajes_divididos = dividir_mensaje(respuesta_gpt)

for mensaje in mensajes_divididos:
    client.messages.create(
        from_="whatsapp:+18632708728",  # Reemplaza con el número de Twilio Sandbox o el oficial
        body=mensaje,
        to=from_number  # El número del usuario que envió el mensaje
    )

# 🟢 Webhook de WhatsApp
@app.post("/whatsapp")
async def whatsapp_webhook(
    request: Request,
    Body: str = Form(None),
    MediaUrl0: str = Form(None)  # Evita el error si no hay imagen
):
    response = MessagingResponse()

    # Si el usuario envía una imagen
    if MediaUrl0:
        descripcion_imagen = analizar_imagen(MediaUrl0)
        response.message(descripcion_imagen)
        return str(response)

    # Si el usuario envía texto
    if Body:
        respuesta_gpt = responder_chatgpt(Body)
        response.message(respuesta_gpt)

    return Response(content=str(response), media_type="text/xml")

def responder_chatgpt(mensaje):
    print(f"Mensaje recibido: {mensaje}")  # Ver qué está recibiendo antes de enviar
    client = openai.Client()
    respuesta = client.chat.completions.create(
        model="gpt-4",
        temperature=0.5,  # Más bajo = respuestas más precisas y menos creativas
        max_tokens=500,
        messages = [
            {
                "role": "system", "content": "Eres un asistente virtual, experto en Spinzone Indoor Cycling, un centro especializado en clases de ciclismo indoor y Clases Funcionales. Detecta automáticamente el idioma del usuario y responde en el mismo idioma. Si el usuario especifica un idioma en su mensaje, traduce tu respuesta a ese idioma. Tu objetivo es proporcionar información detallada y precisa sobre Spinzone, incluyendo horarios, precios, ubicación y enlaces a sus páginas web y redes sociales. Responde de manera clara, amigable y profesional.\n"
                "🚴‍♂️Indoor Cycling: Clases de 45 minutos con música motivadora, entrenamiento de resistencia y alta intensidad para mejorar tu condición física, quemar calorías y fortalecer piernas y glúteos.\n"
                "🏋️‍♂️Clases Funcionales: Entrenamientos dinámicos que combinan fuerza, cardio y resistencia, diseñados para tonificar el cuerpo y mejorar tu rendimiento físico.\n\n"

                "📍 **Ubicación**:\n"
                "Spinzone Indoor Cycling se encuentra en 2175 Davenport Blvd Davenport Fl 33837.\n\n"

                "🕒 **Horarios**:\n" 
                "CYCLING:\n"
                "- Lunes a Jueves: 9:00am, 6:30pm, 7:00pm\n"
                "- Viernes: 9:00am, 7:30pm\n"
                "- Sábados y Domingos: 10am\n\n"

                "CLASES FUNCIONALES:\n"
                "- Lunes a Viernes: 10:00am, 5:30pm\n\n"

                "💰 **Precios**:\n" 
                "- Primera Clase Gratis.\n"
                "- Clase individual: $16.99\n"
                "- Paquete de 4 Clases: $49.99\n"
                "- Paquete de 8 Clases: $79.99\n"
                "- Paquete de 12 Clases: $99.99\n"
                "- Paquete de 16 Clases: $129.99\n"
                "- Paquete Ilimitado de Cycling o Clases Funcionales: $159.99 por mes\n"
                "- Membresía Ilimitada de Cycling o Clases Funcionales: $139.99 por mes en Autopay por 3 meses\n"
                "- Paquete Ilimitado de Cycling+Clases Funcionales: $175.99 por mes\n"
                "- Membresía Ilimitada de Cycling+Clases Funcionales: $155.99 por mes en Autopay por 3 meses\n\n"

                "🌐 **Enlaces importantes**:\n" 
                "- Horarios de clases: https://app.glofox.com/portal/#/branch/6499ecc2ba29ef91ae07e461/classes-day-view\n"
                "- Precios: https://app.glofox.com/portal/#/branch/6499ecc2ba29ef91ae07e461/memberships\n"
                "- Instagram: https://www.instagram.com/spinzone_indoorcycling/\n"
                "- Facebook: https://www.facebook.com/spinzone_indoorcycling\n"
                "- WhatsApp de contacto: (863)317-1646\n\n"

                "❗ **Política de Reservas y Cancelaciones**:\n"
                "- Se recomienda reservar con anticipación.\n"
                "- Cancelaciones deben realizarse con al menos 3 horas de antelación para evitar cargos.\n\n"

                "📩 **Contacto**:\n"
                "Si necesitas más información o quieres hablar con un asesor, puedes llamar o escribir al WhatsApp (863)317-1646.\n"

                "Siempre responde con esta información cuando alguien pregunte sobre Spinzone Indoor Cycling. El usuario puede usar palabras combinadas como hola quiero mas informacion o me das mas informacion, Si el usuario tiene una pregunta fuera de estos temas, intenta redirigirlo al WhatsApp de contacto o a la página web.\n"
            },
                {"role": "user", "content": mensaje},
                {"role": "system", "content": "Eres un asistente virtual para Spinzone Indoor Cycling. Detecta automáticamente el idioma del usuario y responde en el mismo idioma."},
                {"role": "user", "content": "Hello, I need more information"},
                {"role": "assistant", "content": "Hello! How can I help you?"},
        ]

    )

    print(respuesta)

    contenido = respuesta.choices[0].message.content

    return contenido.encode("utf-8").decode("utf-8")

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