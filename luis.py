from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time
import os
from dotenv import load_dotenv
from selenium.webdriver.common.action_chains import ActionChains
from gmail_helper import obtener_codigo_glofox
import gmail_helper
import pyautogui

load_dotenv()


# ✅ **Configurar opciones del navegador**
chrome_options = Options()
chrome_options.add_argument("--start-maximized")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--no-sandbox")

# ✅ **Inicializar WebDriver**
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

def escribir_como_humano(campo, texto, retraso=0.2):
    """ Escribe un texto en un campo letra por letra """
    for letra in texto:
        campo.send_keys(letra)
        time.sleep(retraso)

try:
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
    try:
        print("⏳ Verificando si estamos en la pantalla de ingreso de código...")

        # Esperar que los campos del código estén presentes
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//input[@id='code1']"))
        )

        print("✅ Pantalla de código detectada.")

        # 📩 **Obtener código desde Gmail**
        print("📩 Intentando obtener el código de verificación desde Gmail...")
        codigo_verificacion = gmail_helper.obtener_codigo_glofox()

        if not codigo_verificacion or len(codigo_verificacion) != 6 or not codigo_verificacion.isdigit():
            print(f"❌ ERROR: Código de verificación inválido: {codigo_verificacion}")
            driver.quit()
            exit()

        print(f"✅ Código de verificación obtenido correctamente: {codigo_verificacion}")

        # 🔢 **Ingresar el código en los campos**
        for i, numero in enumerate(codigo_verificacion):
            campo_codigo = driver.find_element(By.ID, f"code{i+1}")

            # **Simular un clic en el campo para activarlo**
            ActionChains(driver).move_to_element(campo_codigo).click().perform()
            time.sleep(0.3)

            # **Intentar escribir con send_keys**
            try:
                campo_codigo.send_keys(numero)
            except:
                print(f"⚠️ No se pudo ingresar el número {numero} con send_keys, intentando con ActionChains...")
                ActionChains(driver).move_to_element(campo_codigo).click().send_keys(numero).perform()

            print(f"✅ Dígito {i+1} ({numero}) ingresado.")
            time.sleep(0.3)  # Simula ingreso humano

        # **Verificar si los números realmente se ingresaron**
        valores_ingresados = [driver.find_element(By.ID, f"code{i+1}").get_attribute("value") for i in range(6)]
        print(f"📋 Valores ingresados en los campos: {''.join(valores_ingresados)}")

        if ''.join(valores_ingresados) != codigo_verificacion:
            print("⚠️ Los valores ingresados no coinciden. Intentando con PyAutoGUI...")

            # **Forzar ingreso de código con PyAutoGUI**
            for numero in codigo_verificacion:
                pyautogui.write(numero, interval=0.2)  # Escribe cada número con un pequeño retraso
            time.sleep(1)

        # **Revisar nuevamente si el código se ingresó correctamente**
        valores_ingresados = [driver.find_element(By.ID, f"code{i+1}").get_attribute("value") for i in range(6)]
        if ''.join(valores_ingresados) != codigo_verificacion:
            print("❌ ERROR: No se logró ingresar el código de verificación.")
            driver.quit()
            exit()

        print(f"✅ Código {codigo_verificacion} ingresado correctamente.")

        # 🔥 **Esperar a que el botón "Iniciar sesión" esté habilitado**
        boton_login_xpath = "//button[contains(text(), 'Iniciar sesión')]"
        boton_login = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, boton_login_xpath))
        )

        # 🔄 **Hacer scroll hasta el botón**
        driver.execute_script("arguments[0].scrollIntoView();", boton_login)

        # 🔘 **Intentar hacer clic en el botón**
        try:
            boton_login.click()
            print("✅ Se hizo clic en 'Iniciar sesión' correctamente.")
        except:
            print("⚠️ No se pudo hacer clic con click(), intentando con JavaScript...")
            driver.execute_script("arguments[0].click();", boton_login)

        print("✅ Se hizo clic en 'Iniciar sesión' después de ingresar el código.")

        # ⏳ **Esperar redirección al Dashboard**
        print("⏳ Esperando redirección al Dashboard...")

        try:
            # Esperamos que cambie la URL (indicación de que el login fue exitoso)
            WebDriverWait(driver, 15).until(EC.url_contains("dashboard"))
            print("✅ Redirección al Dashboard exitosa.")
    
            # También verificamos el título de la página como confirmación
            titulo_pagina = driver.title
            print(f"📌 Título de la página después de MFA: {titulo_pagina}")

        except Exception as e:
            print(f"❌ ERROR: No se detectó la redirección al Dashboard. Posible fallo en el login: {e}")
            print("🔄 Intentando recargar la página y reingresar el código...")
            driver.refresh()
            time.sleep(5)

    except Exception as e:
        print(f"❌ ERROR GENERAL: {e}")
    
        # Guardar captura en el escritorio
        ruta_screenshot = os.path.join(os.path.expanduser("~"), "Desktop", "error_screenshot.png")
        driver.save_screenshot(ruta_screenshot)
    
        print(f"📸 Captura de pantalla guardada en: {ruta_screenshot}")

    # 2️⃣ **Navegar a la sección de Leads**
    try:
        print("⏳ Accediendo al menú de Manage...")

        # 🔍 **Verificar si hay overlays y eliminarlos**
        overlay_classes = ["dashboard-modal_overlay", "dashboard-modal_wrapper", "preloader-inline"]

        for overlay_class in overlay_classes:
            try:
                overlay = driver.find_element(By.CLASS_NAME, overlay_class)
                if overlay.is_displayed():
                    print(f"⚠️ Overlay detectado ({overlay_class}). Eliminándolo...")
                    driver.execute_script("arguments[0].remove();", overlay)
                    time.sleep(1)
            except:
                print(f"✅ No se detectó overlay con clase: {overlay_class}")

        # **Hacer scroll al menú lateral antes de intentar hacer clic**
        menu_lateral = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'ul.primary-menu'))
        )
        print("✅ Scroll al menú lateral...")
        driver.execute_script("arguments[0].scrollIntoView();", menu_lateral)
        time.sleep(1)

        # **Esperar hasta que el botón "Manage" esté presente**
        boton_manage = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="primary-link-item-manage"]'))
        )

        # 🔥 **Forzar visibilidad y habilitación**
        print("🔧 Asegurando que 'Manage' esté visible y habilitado...")
        driver.execute_script("arguments[0].style.visibility = 'visible';", boton_manage)
        driver.execute_script("arguments[0].style.display = 'block';", boton_manage)
        driver.execute_script("arguments[0].removeAttribute('disabled');", boton_manage)

        # **Hacer hover sobre "Manage" antes de hacer clic**
        print("🖱️ Realizando hover sobre 'Manage'...")
        actions = ActionChains(driver)
        actions.move_to_element(boton_manage).perform()
        time.sleep(1)

        # **Intentar hacer clic con diferentes métodos**
        try:
            print("🖱️ Intentando hacer clic con .click()...")
            boton_manage.click()
        except:
            print("⚠️ No se pudo hacer clic con .click(), intentando con JavaScript...")
            driver.execute_script("arguments[0].click();", boton_manage)

        print("✅ Menú 'Manage' abierto.")

        # ⏳ **Esperar la opción "Leads" en el menú**
        print("⏳ Accediendo a Leads...")
        boton_leads = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Leads')]"))
        )

        # Intentar hacer clic en "Leads"
        try:
            print("🖱️ Intentando hacer clic en 'Leads' con .click()...")
            boton_leads.click()
        except:
            print("⚠️ No se pudo hacer clic en 'Leads', intentando con JavaScript...")
            driver.execute_script("arguments[0].click();", boton_leads)

        print("✅ Sección de Leads abierta.")

    except Exception as e:
        print(f"❌ ERROR al intentar abrir el menú 'Manage': {e}")
        driver.save_screenshot("error_screenshot.png")  # Guardar captura de pantalla
        print("📸 Captura de pantalla guardada como 'error_screenshot.png'.")

    time.sleep(2)  # Esperar a que aparezcan las opciones

    print("⏳ Accediendo a Leads...")
    boton_leads_xpath = "//*[@id='content-container--angular']/leads/div[1]/general-header/div/can/div/div/button"  # XPath de la opción "Leads"
    boton_leads = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, boton_leads_xpath)))
    boton_leads.click()
    print("✅ Sección de Leads abierta.")

    # Ingresar detalles del Lead
    lead_nombre = "Carlos"
    lead_apellido = "Pérez"
    lead_email = "carlosperez@test.com"
    lead_telefono = "123456789"
    lead_fecha_nacimiento = "01/01/1995"

    # Llenar los campos
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "firstName"))).send_keys(lead_nombre)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "lastName"))).send_keys(lead_apellido)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "email"))).send_keys(lead_email)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "phone"))).send_keys(lead_telefono)

    # Seleccionar Género
    driver.find_element(By.XPATH, "/html/body/main/div[5]/div[1]/div[2]/div/div[2]/div[1]").click()  # Puedes cambiar a 'Female'

    # Ingresar Fecha de Nacimiento
    campo_fecha = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "/html/body/main/div[5]/div[1]/div[2]/div/div[5]/div[1]")))
    campo_fecha.send_keys(lead_fecha_nacimiento)
    campo_fecha.send_keys(Keys.ENTER)
    print(f"✅ Lead {lead_nombre} {lead_apellido} ingresado.")

    # Guardar Lead
    driver.find_element(By.XPATH, "/html/body/main/div[5]/div[1]/div[3]/div[2]").click()
    print("✅ Nuevo Lead guardado.")

    # 4️⃣ **Asignar Crédito Gratuito**
    time.sleep(3)
    
    # Buscar Lead en la lista
    search_box = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Search Leads']")))
    search_box.send_keys(lead_email)
    time.sleep(2)  # Esperar que cargue el resultado
    
    # Abrir perfil del Lead
    driver.find_element(By.XPATH, f"//div[contains(text(), '{lead_email}')]").click()
    print("✅ Perfil del Lead abierto.")

    # Ir a la sección de Créditos
    driver.find_element(By.XPATH, "//button[contains(text(), 'Credits')]").click()
    time.sleep(2)

    # Agregar un crédito gratuito
    driver.find_element(By.XPATH, "//button[contains(text(), 'Add Credit')]").click()
    time.sleep(1)
    driver.find_element(By.XPATH, "//input[@placeholder='Enter credit amount']").send_keys("1")
    driver.find_element(By.XPATH, "//button[contains(text(), 'Confirm')]").click()
    print("✅ Crédito gratuito asignado.")

    # 5️⃣ **Agendar una Clase**
    driver.get("https://app.glofox.com/dashboard/#/classes")
    time.sleep(3)

    # Seleccionar la primera clase disponible
    clase_disponible = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'Book Now')]")))
    clase_disponible.click()
    print("✅ Clase seleccionada.")

    # Ingresar Lead en la clase
    search_user = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Search for a member']")))
    search_user.send_keys(lead_email)
    time.sleep(2)

    # Seleccionar al usuario
    driver.find_element(By.XPATH, f"//div[contains(text(), '{lead_email}')]").click()
    print("✅ Lead seleccionado para la clase.")

    # Confirmar reserva
    driver.find_element(By.XPATH, "//button[contains(text(), 'Confirm Booking')]").click()
    print("✅ Clase agendada exitosamente para el Lead.")

except Exception as e:
    print(f"❌ ERROR: {e}")

finally:
    time.sleep(5)  # Espera antes de cerrar el navegador
    driver.quit()
