import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from gmail_helper import obtener_codigo_glofox
import pyautogui
from dotenv import load_dotenv

load_dotenv()

# 🚀 Iniciar Chrome en modo indetectable
driver = uc.Chrome()

def escribir_con_pyautogui(texto, retraso=0.3):
    """ Escribe un texto simulando teclado humano con pyautogui """
    for letra in texto:
        pyautogui.write(letra)
        time.sleep(retraso)

def escribir_como_humano(campo, texto, retraso=0.3):
    """ Escribe un texto en un campo letra por letra """
    for letra in texto:
        campo.send_keys(letra)
        time.sleep(retraso)

# 1️⃣ **Abrir la página de login de Glofox**
driver.get("https://app.glofox.com/dashboard/#/glofox/login")
print("🌐 Página de Glofox cargada.")

# 2️⃣ **Ingresar Business Name**
xpath_business = "//input[contains(@placeholder, 'Search for your business')]"
campo_business = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, xpath_business)))
print("✅ Campo de 'Business Name' encontrado.")

business_name = os.getenv("GLOFOX_BUSINESS", "SpinZone")
escribir_como_humano(campo_business, business_name)
print(f"📌 Se escribió en Business Name: {business_name}")

time.sleep(2)  # Esperar a que aparezca la lista desplegable
lista_desplegable = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.XPATH, f"//div[contains(text(), '{business_name}')]"))
)
lista_desplegable.click()
print("✅ Se seleccionó el negocio correctamente.")

driver.find_element(By.TAG_NAME, "body").click()
time.sleep(2)

# 3️⃣ **Ingresar Email**
campo_email = WebDriverWait(driver, 10).until(
    EC.element_to_be_clickable((By.XPATH, "//input[contains(@placeholder, 'Enter your email address')]"))
)
print("✅ Campo de email encontrado.")

# Forzar visibilidad del campo de email con JavaScript
driver.execute_script("""
    let campo = arguments[0];
    campo.removeAttribute('disabled');
    campo.removeAttribute('readonly');
    campo.style.display = 'block';
    campo.style.visibility = 'visible';
    campo.style.opacity = '1';
    campo.focus();
""", campo_email)
time.sleep(1)

email = "spinzonechatbot@gmail.com"
campo_email.click()
campo_email.clear()
escribir_como_humano(campo_email, email)
print(f"✅ Email ingresado: {email}")

# 4️⃣ **Ingresar Contraseña**
campo_password = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.XPATH, "//input[contains(@placeholder, 'Enter your password')]"))
)
print("✅ Campo de contraseña encontrado.")

# Habilitar el campo de contraseña
driver.execute_script("""
    let campo = arguments[0];
    campo.removeAttribute('disabled');
    campo.removeAttribute('readonly');
    campo.style.display = 'block';
    campo.style.visibility = 'visible';
    campo.style.opacity = '1';
    campo.focus();
""", campo_password)
time.sleep(1)

# Escribir la contraseña letra por letra
password = os.getenv("GLOFOX_PASSWORD")
if not password:
    print("❌ ERROR: La variable de entorno GLOFOX_PASSWORD no está definida.")
    driver.quit()
    exit()

campo_password.click()
campo_password.clear()
escribir_como_humano(campo_password, password)
print("✅ Contraseña ingresada correctamente.")

# 5️⃣ **Hacer clic en el botón de Login**
boton_login = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.XPATH, "//*[@id='content-container--angular']/div/entry-login/div/div/form/div[2]/component-button"))
)

# Verificar si el botón está deshabilitado
esta_deshabilitado = driver.execute_script("return arguments[0].disabled;", boton_login)
if esta_deshabilitado:
    print("⚠️ El botón de Login está deshabilitado. Intentando habilitarlo...")
    driver.execute_script("arguments[0].removeAttribute('disabled');", boton_login)

ActionChains(driver).move_to_element(boton_login).click().perform()
print("✅ Se hizo clic en el botón de Login.")

# 6️⃣ **Esperar la pantalla de código de verificación**
WebDriverWait(driver, 20).until(
    EC.presence_of_element_located((By.ID, "code1"))
)
print("⏳ Campos de código de verificación detectados.")

# 📩 **Obtener el código MFA**
print("📩 Buscando código de verificación en Gmail...")
codigo_verificacion = obtener_codigo_glofox()
if not codigo_verificacion or len(codigo_verificacion) != 6:
    print("❌ ERROR: No se pudo obtener un código válido.")
    driver.quit()
    exit()
print(f"✅ Código de verificación obtenido: {codigo_verificacion}")

# 🔥 **Forzar el foco en el campo MFA**
print("📍 Localizando los campos MFA...")

campos_codigo = []
for i in range(6):
    try:
        campo = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, f"code{i+1}"))
        )
        campos_codigo.append(campo)
    except:
        print(f"⚠️ No se encontró el campo code{i+1}")

if len(campos_codigo) != 6:
    print("❌ ERROR: No se encontraron los 6 campos de código.")
    driver.quit()
    exit()

print("✅ Campos MFA detectados.")

# 🔄 **Forzar visibilidad y habilitar los campos con JavaScript**
for i, campo in enumerate(campos_codigo):
    driver.execute_script("""
        arguments[0].removeAttribute('disabled');
        arguments[0].removeAttribute('readonly');
        arguments[0].style.display = 'block';
        arguments[0].style.visibility = 'visible';
        arguments[0].style.opacity = '1';
        arguments[0].focus();
    """, campo)
    print(f"✅ Campo {i+1} activado.")

# **Intentar escribir el código con Selenium**
try:
    for i, numero in enumerate(codigo_verificacion):
        ActionChains(driver).move_to_element(campos_codigo[i]).click().perform()
        time.sleep(0.2)
        campos_codigo[i].send_keys(numero)
        time.sleep(0.3)
        driver.execute_script("""
            let event = new Event('input', { bubbles: true });
            arguments[0].dispatchEvent(event);
        """, campos_codigo[i])
    print("✅ Código ingresado con Selenium.")
except:
    print("⚠️ No se pudo escribir con Selenium. Intentando con JavaScript...")

    # **Forzar ingreso con JavaScript**
    for i, numero in enumerate(codigo_verificacion):
        driver.execute_script(f"arguments[0].value = '{numero}';", campos_codigo[i])
        driver.execute_script("""
            let event = new Event('input', { bubbles: true });
            arguments[0].dispatchEvent(event);
        """, campos_codigo[i])

# **Verificar si el código realmente se escribió**
codigo_ingresado = "".join([campo.get_attribute("value") or "" for campo in campos_codigo])

if codigo_ingresado != codigo_verificacion:
    print(f"⚠️ Código en pantalla: {codigo_ingresado}, Código esperado: {codigo_verificacion}")
    print("❌ ERROR: No se ingresó correctamente el código.")
    driver.save_screenshot("error_codigo.png")
    print("📸 Captura de pantalla guardada como 'error_codigo.png'.")
    driver.quit()
    exit()
else:
    print("✅ Código verificado correctamente.")

# ⏳ **Esperar el botón "Iniciar Sesión"**
print("⏳ Buscando botón 'Iniciar sesión' después del MFA...")

try:
    boton_verificar = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Iniciar sesión')]"))
    )
    boton_verificar.click()
    print("✅ Se hizo clic en 'Iniciar sesión'.")
except:
    print("⚠️ No se pudo hacer clic en el botón, intentando con ENTER...")
    try:
        driver.execute_script("arguments[0].dispatchEvent(new KeyboardEvent('keydown', {'key': 'Enter'}));", campos_codigo[-1])
        driver.execute_script("arguments[0].dispatchEvent(new KeyboardEvent('keyup', {'key': 'Enter'}));", campos_codigo[-1])
    except:
        print("❌ ERROR: No se pudo presionar ENTER en el campo.")

# ⏳ **Esperar redirección al Dashboard**
try:
    WebDriverWait(driver, 15).until(EC.url_contains("dashboard"))
    print("✅ Redirección al Dashboard exitosa.")
except:
    print("❌ ERROR: No se detectó la redirección al Dashboard.")
    driver.save_screenshot("error_dashboard.png")
    print("📸 Captura de pantalla guardada como 'error_dashboard.png'.")
    input("🛑 Verifica el navegador. Presiona Enter para cerrar...")
    driver.quit()
    exit()

# 🛑 **Evitar que el navegador se cierre automáticamente**
input("⏳ Presiona Enter para cerrar el navegador después de verificar todo...")
driver.quit()