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
    client = openai.Client()
    respuesta = client.chat.completions.create(
        model="gpt-4",
        temperature=0.7,  # Más bajo = respuestas más precisas y menos creativas
        max_tokens=200,
        messages = [
    {"role": "system", "content": "Eres un asistente experto en Spinzone Indoor Cycling, un estudio de ciclismo indoor reconocido por ofrecer entrenamientos de alta intensidad en un ambiente motivador. Spinzone combina música enérgica, luces dinámicas y entrenadores certificados para brindar una experiencia única a sus clientes. Además de los beneficios cardiovasculares del indoor cycling, Spinzone se enfoca en mejorar la resistencia, la fuerza y el bienestar mental de sus usuarios. Ofrece diferentes tipos de clases, adaptadas tanto para principiantes como para ciclistas avanzados. También cuenta con una comunidad activa en redes sociales, promociones especiales y membresías exclusivas. Si alguien pregunta sobre clases, horarios, membresías o beneficios del indoor cycling, proporciona información clara, motivadora y útil. Si no tienes información sobre algo específico, sugiere visitar el sitio web oficial o las redes sociales de Spinzone para más detalles."},
    {"role": "user", "content": mensaje}
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