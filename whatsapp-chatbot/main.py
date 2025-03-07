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

def es_similar(frase_usuario, opciones, umbral=70):
    """Compara el mensaje del usuario con una lista de opciones y devuelve True si es similar."""
    mejor_coincidencia, score = process.extractOne(frase_usuario, opciones)
    return mejor_coincidencia if score >= umbral else None


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

# 🟢 Webhook de WhatsApp
@app.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    try:
        form_data = await request.form()  # Leer los datos correctamente
        print(f"Datos recibidos: {form_data}")  # Log para depuración

        mensaje = form_data.get("Body", "").strip()  # Extraer el mensaje enviado por el usuario
        numero = form_data.get("From", "")  # Extraer el número de teléfono del usuario

        if not mensaje:
            return JSONResponse(content={"error": "Mensaje vacío"}, status_code=400)

        print(f"Mensaje recibido: {mensaje} de {numero}")

        return PlainTextResponse("Recibido correctamente", status_code=200)

    except Exception as e:
        print(f"Error procesando datos: {e}")  # Log del error
        return JSONResponse(content={"error": "Error procesando la solicitud"}, status_code=400)

def responder_chatgpt(mensaje):
    print(f"Mensaje clave detectado: {mensaje_clave}")

    client = openai.Client()
    
    # Palabras clave detectadas con fuzzy matching
    opciones_horario = ["horario", "horarios", "qué horario tienen?", "dime los horarios"]
    opciones_precios = ["precios", "cuánto cuesta", "planes", "tarifas", "costos"]
    opciones_info = ["información", "quiero información", "dame más información", "cuéntame sobre spinzone"]
    
    mensaje_clave = None
    
    if es_similar(mensaje.lower(), opciones_horario):
        mensaje_clave = "Dime los horarios de Spinzone Indoor Cycling."
    elif es_similar(mensaje.lower(), opciones_precios):
        mensaje_clave = "Dime los precios de Spinzone Indoor Cycling."
    elif es_similar(mensaje.lower(), opciones_info):
        mensaje_clave = "Dame información general sobre Spinzone Indoor Cycling."
    else:
        mensaje_clave = mensaje  # Si no hay coincidencias, usa el mensaje original
    
    respuesta = client.chat.completions.create(
        model="gpt-4",
        temperature=0.4,
        max_tokens=1500,
        messages=[
            {
                "role": "system", "content": "Eres un asistente virtual, de Spinzone Indoor Cycling, un centro especializado en clases de ciclismo indoor y Clases Funcionales. Tu objetivo es proporcionar información detallada y precisa sobre Spinzone. Si el usuario pregunta algo relacionado con horarios, precios, ubicación, o información en general, responde con los detalles correspondientes de Spinzone. No esperes coincidencias exactas de palabras clave; detecta la intención del usuario. Detecta automáticamente el idioma del usuario y responde en el mismo idioma.\n"
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
                {"role": "system", "content": prompt_negocio},
                {"role": "user", "content": mensaje_clave}
        ]
    )

    texto_respuesta = respuesta.choices[0].message.content.strip()
    mensajes_divididos = dividir_mensaje(texto_respuesta)

    print(f"Mensajes a enviar: {mensajes_divididos}")  # Depuración


    return dividir_mensaje(texto_respuesta)  # Separa en partes si es necesario

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