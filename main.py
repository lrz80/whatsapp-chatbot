import uvicorn
import os
from fastapi import FastAPI, Request
import openai
from openai import OpenAI
import requests
from twilio.rest import Client
from langdetect import detect, detect_langs
from dotenv import load_dotenv
import aiohttp
import tempfile
import re
from typing import Optional

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

# === NUEVO: memoria simple de idioma por usuario ===
LAST_LANG_BY_NUMBER: dict[str, str] = {}  # e.g., {"whatsapp:+1xxxx": "en"}

# === NUEVO: normalizador del número (asegura prefijo whatsapp:) ===
def normalize_wa(from_value: str) -> str:
    if not from_value:
        return ""
    from_value = from_value.strip()
    return from_value if from_value.startswith("whatsapp:") else f"whatsapp:{from_value}"

# === NUEVO: heurística de override por intención explícita del usuario ===
def explicit_lang_override(text: str) -> Optional[str]:
    t = text.lower().strip()

    # Inglés explícito
    if re.search(r"\b(english please|in english|english)\b", t):
        return "en"

    # Español explícito
    if re.search(r"\b(en español|spanish please|español|habla español)\b", t):
        return "es"

    return None

# === NUEVO: detección segura con fallback por historial, longitud y palabras clave ===
def detectar_idioma_seguro(mensaje: str, numero: str) -> str:
    # 1) Si el usuario lo pidió explícito, respetar
    override = explicit_lang_override(mensaje)
    if override in ("es", "en"):
        LAST_LANG_BY_NUMBER[numero] = override
        print(f"🔄 Override de idioma por solicitud explícita: {override}")
        return override

    # 2) Si ya tenemos idioma previo “confiable” para este número, úsalo para mensajes muy cortos
    palabras = mensaje.strip().split()
    last = LAST_LANG_BY_NUMBER.get(numero)

    # Algunas palabras cortas que confunden a langdetect (e.g., "cycling" -> "cy")
    # Si el texto es corto o es una palabra típica, heredar idioma previo (si existe)
    palabras_conflictivas = {"cycling", "hola", "hello", "ok", "thanks", "gracias", "schedule"}
    if len(palabras) <= 2 or mensaje.lower().strip() in palabras_conflictivas:
        if last in ("es", "en"):
            print(f"🛟 Fallback por mensaje corto/palabra conflictiva → usando idioma previo: {last}")
            return last

    # 3) Detección probabilística (detect_langs) y reglas para ‘cy’
    try:
        langs = detect_langs(mensaje)
        # langs es una lista como [en:0.99, es:0.01]
        # Tomar el top-1
        top = sorted(langs, key=lambda x: x.prob, reverse=True)[0]
        cand = top.lang
        prob = top.prob
        print(f"🔍 detect_langs → {[(str(l.lang), float(l.prob)) for l in langs]} | top={cand} p={prob:.2f}")

        # Si detecta 'cy' para algo como "cycling", mapear a en (muy común)
        if cand == "cy":
            cand = "en"

        # Si el candidato no es es/en, elegir el último si existe; si no, heurística por caracteres
        if cand not in ("es", "en"):
            if last in ("es", "en"):
                print(f"🛟 cand {cand} no válido; usando last={last}")
                return last
            # Heurística por tildes/ñ → español
            if re.search(r"[áéíóúñü]", mensaje.lower()):
                cand = "es"
            else:
                cand = "en"

        # Pequeña confianza: si prob baja (<0.70) y hay last, preferir last
        if prob < 0.70 and last in ("es", "en"):
            print(f"🛟 prob baja ({prob:.2f}); usando last={last}")
            cand = last

        LAST_LANG_BY_NUMBER[numero] = cand
        return cand

    except Exception as e:
        print(f"⚠️ Error en detect_langs: {e}")
        # Fallback: usar last si hay, si no, inglés por defecto
        if last in ("es", "en"):
            return last
        return "en"

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
        numero_raw = form_data.get("From", "").strip()
        numero = normalize_wa(numero_raw)

        print(f"📨 Mensaje recibido: {mensaje} de {numero}")

        # === NUEVO: idioma seguro usando historial + heurísticas
        idioma_usuario = detectar_idioma_seguro(mensaje, numero)
        print(f"🔤 Idioma efectivo para responder: {idioma_usuario}")

        respuesta = responder_chatgpt(mensaje, idioma_usuario)  # ← pasamos idioma
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

# 🚀 Respuestas con OpenAI (con idioma forzado/efectivo)
def responder_chatgpt(mensaje: str, idioma_efectivo: str = "en"):
    print(f"📩 Mensaje recibido: {mensaje}")

    prompt_negocio = {
        "es": """
    Responde como asistente virtual de Synergy Zone (Spinzone). Da respuestas claras, directas y profesionales.
    Evita mensajes genéricos y solo proporciona información relevante según la pregunta del usuario.

    📍 **Ubicación**: Synergy Zone - 2175 Davenport Blvd Davenport Fl 33837.
    🕒 **Horarios**:
    CYCLING:
    - Lunes a Jueves: 6:00am, 9:00am, 6:30pm, 7:30pm
    - Viernes: 6:00am, 9:00am, 6:30pm
    - Sábados y Domingos: 10:00am
    CLASES FUNCIONALES:
    - Lunes a Jueves: 7:00am, 8:15am, 10:00am, 5:30pm, 6:30pm
    - Viernes: 7:00am, 8:15am, 5:30pm
    💰 **Precios**:
    - Primera Clase Gratis.
    - Clase individual: $19.99
    - Paquete de 4 Clases: $59.99
    - Paquete de 8 Clases: $99.99
    - Paquete de 12 Clases: $119.99
    - Plan Bronze Ilimitado de Cycling o Clases Funcionales: $169.99 al mes o $149.99 al mes en Autopay durante 3 meses.
    - Plan Gold Ilimitado de Clases de Cycling y Clases Funcionales + 5% de descuento en tienda: $185.99 al mes o $165.99 al mes en Autopay durante 3 meses.
    - Plan Platinum Ilimitado de Clases de Cycling y Clases Funcionales + 8 Recovery Session (sauna + cold plunge) + 10% de decuento en tienda: $219.99 al mes o $199.99 al mes en autopay durante 3 meses.
    - Plan VIP Full Access (Cupos Limitados): Clases ilimitadas de Cycling y Funcionales + Recovery Session (Sauna + cold plunge) + Kit de Bienvenida + Clase Privada de Cumpleanos $319.99 al mes o $299.99 al mes en Autopay durante 3 meses.
    - Sesion de Sauna (30 Minutos): $14.99
    📲 **Soporte**: https://wa.me/18633171646.
    🌐 **Enlaces**:
    - Reservas: https://app.glofox.com/portal/#/branch/6499ecc2ba29ef91ae07e461/classes-day-view
    - Precios: https://app.glofox.com/portal/#/branch/6499ecc2ba29ef91ae07e461/memberships
    - Clase Gratis: https://app.glofox.com/portal/#/branch/6499ecc2ba29ef91ae07e461/memberships/64bd9335561ca2443a00eb16/plan/1690145417424/buy. 
    ❗ **Política**:
    - Se puede cancelar una clase y devolverla al crédito personal hasta 3 horas antes de la hora programada.
    - Las cancelaciones tardías y las ausencias están sujetas a una tarifa. Las clases no son acumulables y deben usarse dentro del mes.
    - No proporcionamos ni rentamos zapatos de ciclismo, pero las bicicletas permiten el uso tanto de zapatos deportivos comunes como de zapatos con cleats SPD.
    - Los menores de 18 años no pueden registrarse ni crear cuenta en la aplicación; deben inscribirse presencialmente en el estudio con su representante legal.
    - Los Paquetes de creditos se pueden usar en cycling y clases funcionales, cada clase equivale a un credito. Todos nuestros paquetes de creditos y planes tienen una validez de 1 mes y no son acumulables ni transferibles.
    - Se recomienda reservar la clase con anticipacion, aceptamos walk in pero no garantizamos espacio disponible.
    - Todos nuestros paquetes de creditos y planes tienen una validez de 1 mes y no son acumulables ni transferibles. 
    - Rentamos el estudio para clases de cumpleanos, el precio es de $300 incluye 45 minutos de clase, el instructor y espacio para 30 personas, debe hacerse la reservacion con 7 dias de anticipacion y un deposito del 50% es requerido.

    === MODO VENDEDOR (ALTO DESEMPEÑO) ===
    - Objetivo: convertir consultas en reservas o compras sin ser invasivo. Persuade con claridad, beneficios y próximos pasos.
    - Enfoque: primero entender → luego proponer → cerrar con un CTA concreto.
    - Nunca inventes beneficios, precios, cupos ni promociones. Usa EXCLUSIVAMENTE lo que esté en este prompt y ENLACES_OFICIALES.

    1) Descubrimiento (máx. 1 línea)
    - Haz 1 pregunta útil para perfilar necesidad/objetivo (p.ej., “¿Buscas cycling, funcional o ambas?”).
    - Si el usuario ya lo dijo, NO repreguntes.

    2) Beneficios y encaje
    - Resalta 1-2 beneficios RELEVANTES a lo que pidió (extraídos del prompt). Evita genéricos.
    - Si mencionan “primera clase gratis”, refuérzala (“de cortesía”) como vía de entrada.

    3) Oferta y anclaje
    - Sugiere el plan/paquete MÁS adecuado según lo dicho (no sugieras planes que no existan).
    - Si preguntan por algo que NO existe (p.ej., plan para 2): dilo claramente y redirige al plan más cercano + enlace de precios.

    4) Urgencia ética
    - Usa urgencia ligera basada en hechos del prompt (p.ej., “recomendamos reservar con anticipación; los cupos se agotan”).
    - NO inventes escasez ni promociones.

    5) Cierre con CTA único y claro
    - Termina SIEMPRE con un paso accionable:
    • “Reserva aquí: https://app.glofox.com/portal/#/branch/6499ecc2ba29ef91ae07e461/classes-day-view”
    • “Planes y precios: https://app.glofox.com/portal/#/branch/6499ecc2ba29ef91ae07e461/memberships”
    • “Clase de cortesía: https://app.glofox.com/portal/#/branch/6499ecc2ba29ef91ae07e461/memberships/64bd9335561ca2443a00eb16/plan/1690145417424/buy.”
    - Máximo 2 enlaces por respuesta (y 1 por tema).

    6) Manejo de objeciones (breve)
    - Precio: destaca packs/Autopay si aportan valor real.
    - Tiempo/horarios: comparte “Horarios y reservas: https://app.glofox.com/portal/#/branch/6499ecc2ba29ef91ae07e461/classes-day-view”.
    - Dudas: ofrece soporte solo si lo piden o si es necesario: “Soporte: https://wa.me/18633171646”.

    7) Tono
    - Cercano, profesional y proactivo. Sin presión. 2-3 líneas + CTA.
    """,
        "en": """
    Reply as the virtual assistant for Synergy Zone (Spinzone). Keep answers clear, direct, and professional.
    Avoid generic messages and provide only information relevant to the user's question.

    📍 **Location**: Synergy Zone - 2175 Davenport Blvd, Davenport, FL 33837.
    🕒 **Schedule**:
    CYCLING:
    - Monday-Thursday: 6:00am, 9:00am, 6:30pm, 7:30pm
    - Friday: 6:00am, 9:00am, 6:30pm
    - Saturday & Sunday: 10:00am
    FUNCTIONAL CLASSES:
    - Monday-Thursday: 7:00am, 8:15am, 10:00am, 5:30pm, 6:30pm
    - Friday: 7:00am, 8:15am, 5:30pm
    💰 **Pricing**:
    - First class free (complimentary).
    - Single class: $19.99
    - 4-Class Pack: $59.99
    - 8-Class Pack: $99.99
    - 12-Class Pack: $119.99
    - Bronze Unlimited (Cycling or Functional): $169.99/mo or $149.99/mo on Autopay for 3 months.
    - Gold Unlimited (Cycling + Functional) + 5% in-store discount: $185.99/mo or $165.99/mo on Autopay for 3 months.
    - Platinum Unlimited (Cycling + Functional) + 8 Recovery Sessions (sauna + cold plunge) + 10% in-store discount: $219.99/mo or $199.99/mo on Autopay for 3 months.
    - VIP Full Access (Limited spots): Unlimited Cycling & Functional + Recovery Session (Sauna + Cold Plunge) + Welcome Kit + Private Birthday Class: $319.99/mo or $299.99/mo on Autopay for 3 months.
    - Sauna session (30 minutes): $14.99
    📲 **Support**: https://wa.me/18633171646
    🌐 **Links**:
    - Bookings: https://app.glofox.com/portal/#/branch/6499ecc2ba29ef91ae07e461/classes-day-view
    - Pricing: https://app.glofox.com/portal/#/branch/6499ecc2ba29ef91ae07e461/memberships
    - Free class: https://app.glofox.com/portal/#/branch/6499ecc2ba29ef91ae07e461/memberships/64bd9335561ca2443a00eb16/plan/1690145417424/buy

    ❗ **Policy**:
    - You can cancel a class and return it to your personal credit up to 3 hours before the scheduled time.
    - Late cancellations and no-shows are subject to a fee. Classes are not cumulative and must be used within the month.
    - We do not provide or rent cycling shoes; bikes support regular athletic shoes or SPD cleat shoes.
    - Minors under 18 cannot register or create an account in the app; they must enroll in person at the studio with their legal guardian.
    - Credit packs can be used for cycling and functional classes; each class equals 1 credit. All packs and plans are valid for 1 month and are neither cumulative nor transferable.
    - We recommend booking in advance; walk-ins are accepted but space is not guaranteed.
    - We rent the studio for birthday classes: $300 includes a 45-minute class, the instructor, and space for up to 30 people. Must be booked 7 days in advance with a 50% deposit.

    === SALES MODE (TOP PERFORMANCE) ===
    - Goal: turn inquiries into bookings or purchases without being pushy. Be clear, benefit-driven, and action-oriented.
    - Flow: understand → propose → close with a concrete CTA.
    - Never invent benefits, prices, availability, or promos. Use ONLY data in this prompt and OFFICIAL_LINKS.

    1) Discovery (max 1 line)
    - Ask 1 useful profiling question (e.g., “Are you interested in cycling, functional, or both?”).
    - If the user already said it, do NOT re-ask.

    2) Benefits & fit
    - Highlight 1–2 RELEVANT benefits (from the prompt). Avoid generic fluff.
    - If “first class free” appears, reinforce it as a low-friction entry.

    3) Offer & anchor
    - Propose the MOST suitable plan/package based on their need (don’t suggest non-existent plans).
    - If they ask for something NOT available (e.g., duo plan): say so clearly and redirect to the closest option + pricing link.

    4) Ethical urgency
    - Use light, truthful urgency from the prompt (e.g., “we recommend booking in advance; spots can fill up”).
    - Do NOT invent scarcity or promos.

    5) Close with a single, clear CTA
    - Always end with one actionable step:
    • “Book here: https://app.glofox.com/portal/#/branch/6499ecc2ba29ef91ae07e461/classes-day-view”
    • “Plans & pricing: https://app.glofox.com/portal/#/branch/6499ecc2ba29ef91ae07e461/memberships”
    • “Complimentary class: https://app.glofox.com/portal/#/branch/6499ecc2ba29ef91ae07e461/memberships/64bd9335561ca2443a00eb16/plan/1690145417424/buy”
    - Max 2 links per reply (and 1 per topic).

    6) Objection handling (brief)
    - Price: point to packs/Autopay if they provide real value.
    - Time/schedule: “Schedules & bookings: https://app.glofox.com/portal/#/branch/6499ecc2ba29ef91ae07e461/classes-day-view”.
    - Extra doubts: offer support only if requested or needed: “Support: https://wa.me/18633171646”.

    7) Tone
    - Friendly, professional, proactive. No pressure. 2-3 lines + CTA.
    """
    }

    # Elegir prompt por idioma ya decidido
    prompt_seleccionado = prompt_negocio["en" if idioma_efectivo == "en" else "es"]

    try:
        respuesta_openai = openai.chat.completions.create(
            model="gpt-4",
            temperature=0.3,      # Respuestas más directas
            max_tokens=800,       # Evita superar límites de Twilio
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
