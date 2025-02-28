import os
from fastapi import FastAPI, Request, Form
import openai
import requests
import uvicorn
from twilio.twiml.messaging_response import MessagingResponse

# Configura las API Keys
OPENAI_API_KEY = "tu_openai_api_key"
TWILIO_NUMBER = "tu_numero_twilio"
TWILIO_AUTH_TOKEN = "tu_auth_token"
TWILIO_SID = "tu_twilio_sid"

# Inicializa FastAPI
app = FastAPI()
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
    MediaUrl0: str = Form(None),
    From: str = Form(None)
):
    response = MessagingResponse()

    # Si el usuario envía una imagen
    if MediaUrl0:
        descripcion_imagen = analizar_imagen(MediaUrl0)
        response.message(descripcion_imagen)
        return str(response)

    # Si el usuario envía un mensaje de texto
    if Body:
        mensaje = Body.lower().strip()

        # Responder con mensajes predefinidos
        if mensaje in RESPUESTAS_PERSONALIZADAS:
            response.message(RESPUESTAS_PERSONALIZADAS[mensaje])
            return str(response)

        # Responder con ChatGPT
        respuesta_gpt = responder_chatgpt(mensaje)
        response.message(respuesta_gpt)
        return str(response)

    return str(response)

# Configurar la API Key
openai.api_key = "tu_openai_api_key"

def responder_chatgpt(mensaje):
    client = openai.Client()  # Se debe usar un cliente en OpenAI 1.64.0
    respuesta = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": mensaje}]
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

# Leer el puerto asignado por Railway
PORT = int(os.environ.get("PORT", 8000))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)