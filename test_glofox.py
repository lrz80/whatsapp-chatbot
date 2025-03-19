import undetected_chromedriver.v2 as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# 🚀 Iniciar Chrome en modo indetectable
driver = uc.Chrome()

# Ir a la página de login de Glofox
driver.get("https://app.glofox.com/dashboard/#/glofox/login")

# Esperar hasta que se muestre el campo de email
WebDriverWait(driver, 20).until(
    EC.presence_of_element_located((By.XPATH, "//input[contains(@placeholder, 'Enter your email address')]"))
)

print("✅ Página de login cargada correctamente.")

# 💡 Ahora puedes continuar con la autenticación MFA como antes...

