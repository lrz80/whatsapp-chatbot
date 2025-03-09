import uvicorn
import os
from fastapi import FastAPI, Request, Form
import openai
import requests
import subprocess
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
from pydub import AudioSegment
import speech_recognition as sr
import aiofiles  # Para manejar archivos de manera asíncrona

# Configurar el path de ffmpeg para pydub
os.environ["FFMPEG_EXECUTABLE"] = "C:\\ffmpeg\\ffmpeg-7.1-essentials_build\\bin\\ffmpeg.exe"

def procesar_audio(url_audio):
    try:
        response = requests.get(url_audio)
        if response.status_code != 200:
            print(f"❌ Error al descargar el audio. Código HTTP: {response.status_code}")
            return None

        ruta_mp3 = "audio_recibido.mp3"
        with open(ruta_mp3, "wb") as file:
            file.write(response.content)
        
        print(f"✅ Audio guardado correctamente: {ruta_mp3}")

        # Convertir el audio a WAV (PCM 16-bit, 16kHz) usando FFmpeg
        ruta_wav = "audio_recibido.wav"
        comando = f"ffmpeg -i {ruta_mp3} -acodec pcm_s16le -ar 16000 {ruta_wav}"
        subprocess.run(comando, shell=True, check=True)
        
        print(f"✅ Audio convertido a WAV: {ruta_wav}")

        return ruta_wav  # Retorna la nueva ruta del archivo WAV

    except Exception as e:
        print(f"❌ Error en el procesamiento del audio: {e}")
        return None


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

def transcribir_audio(audio_url: str) -> str:
    try:
        subprocess.run(["ffmpeg", "-version"], check=True)
        print("✔ FFmpeg está instalado y funcionando correctamente.")
    except FileNotFoundError:
        print("❌ Error: FFmpeg no está instalado.")
    try:
        # Descargar el audio desde Twilio
        response = requests.get(audio_url)
        if response.status_code != 200:
            return "❌ Error al descargar el audio."

        # Guardar el archivo temporalmente en formato MP3
        ruta_mp3 = "audio_recibido.mp3"
        with open(ruta_mp3, "wb") as f:
            f.write(response.content)

        # 🔍 Verificar si el archivo MP3 se descargó correctamente
        if os.path.exists(ruta_mp3):
            print(f"✔ Archivo MP3 descargado. Tamaño: {os.path.getsize(ruta_mp3)} bytes")
        else:
            print("❌ Error: El archivo MP3 no se descargó correctamente.")
            return "No se pudo procesar la nota de voz."

        # Convertir MP3 a WAV con FFmpeg
        ruta_wav = "audio_recibido.wav"
        comando = [
            "ffmpeg", "-y", "-i", ruta_mp3,
            "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", ruta_wav
        ]

        try:
            resultado = subprocess.run(comando, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"✔ Conversión a WAV exitosa: {ruta_wav}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Error en FFmpeg: {e.stderr.decode()}")
            return "No se pudo procesar la nota de voz."

        # 🔍 Verificar si el archivo WAV se generó correctamente
        if os.path.exists(ruta_wav):
            print(f"✔ Archivo WAV listo. Tamaño: {os.path.getsize(ruta_wav)} bytes")
        else:
            print("❌ Error: No se generó correctamente el archivo WAV.")
            return "No se pudo procesar la nota de voz."

        # Crear el cliente de OpenAI
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Enviar el audio a Whisper para transcripción
        with open(ruta_wav, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )

        return transcript.text  # ✔ Retorna el texto transcrito

    except Exception as e:
        print(f"❌ Error en la transcripción: {e}")
        return "No se pudo entender el audio. Intenta de nuevo."

    
def descargar_audio(url_audio):
    """ Descarga un archivo de audio desde Twilio con autenticación """
    try:
        print(f"🔗 Intentando descargar: {url_audio}")

        # Validar si la URL es correcta
        if not url_audio.startswith("http"):
            print(f"❌ URL inválida: {url_audio}")
            return None

        # Verificar que las credenciales no estén vacías
        if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
            print("❌ ERROR: Credenciales de Twilio no definidas.")
            return None

        # Realizar la solicitud con autenticación
        response = requests.get(url_audio, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN), stream=True)

        if response.status_code == 401:
            print("❌ ERROR: Autenticación fallida (HTTP 401). Verifica las credenciales de Twilio.")
            return None
        elif response.status_code != 200:
            print(f"❌ Error al descargar el audio. Código HTTP: {response.status_code}")
            return None

        # Guardar el archivo
        ruta_mp3 = "audio_recibido.mp3"
        with open(ruta_mp3, "wb") as file:
            file.write(response.content)
            print(f"Tamaño del archivo descargado: {os.path.getsize(ruta_mp3)} bytes")


        # Verificar que el archivo fue guardado correctamente
        if os.path.exists(ruta_mp3) and os.path.getsize(ruta_mp3) > 0:
            print(f"✅ Audio guardado correctamente: {ruta_mp3}")
            return ruta_mp3
        else:
            print("❌ ERROR: No se pudo guardar el audio.")
            return None

    except Exception as e:
        print(f"❌ ERROR en descarga de audio: {e}")
        return None
    
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
        form_data = await request.form()
        mensaje = form_data.get("Body", "").strip()
        url_audio = form_data.get("MediaUrl0")  # Usar la clave correcta

        if url_audio:
            print(f"🎤 Nota de voz recibida: {url_audio}")
            ruta_wav = procesar_audio(url_audio)  # Obtiene el archivo convertido
            if ruta_wav:
                mensaje = transcribir_audio(ruta_wav)  # Transcribe el audio
                print(f"📝 Transcripción: {mensaje}")


        if not mensaje:
            return PlainTextResponse("Mensaje vacío", status_code=400)

        respuesta = responder_chatgpt(mensaje)
        return PlainTextResponse(respuesta, status_code=200)

    except Exception as e:
        print(f"❌ Error procesando datos: {e}")
        return PlainTextResponse("Error interno del servidor", status_code=500)

# Función para procesar el audio recibido
def procesar_audio(url_audio):
    try:
        response = requests.get(url_audio)
        ruta_mp3 = "audio_recibido.mp3"

        with open(ruta_mp3, "wb") as file:
            file.write(response.content)

        return ruta_mp3

    except Exception as e:
        print(f"❌ Error al descargar el audio: {e}")
        return None

# Función para transcribir el audio
def transcribir_audio(ruta_mp3):
    try:
        audio = AudioSegment.from_file(ruta_mp3, format="mp3")
        ruta_wav = "audio_recibido.wav"
        audio.export(ruta_wav, format="wav")

        recognizer = sr.Recognizer()
        with sr.AudioFile(ruta_wav) as source:
            audio_data = recognizer.record(source)
            texto = recognizer.recognize_google(audio_data, language="es-EN")
        
        return texto

    except Exception as e:
        print(f"❌ Error en la transcripción: {e}")
        return "No se pudo procesar la nota de voz."


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

# Obtener el puerto desde las variables de entorno de Railway
PORT = int(os.environ.get("PORT", 8000))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)