#!/bin/bash

echo "🔹 Instalando Google Chrome y Chromedriver en Railway..."

# Instalar dependencias necesarias
apt-get update && apt-get install -y wget unzip curl

# Descargar e instalar Google Chrome
wget -q -O google-chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
dpkg -i google-chrome.deb || apt-get install -fy

# Descargar e instalar ChromeDriver
CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | cut -d '.' -f 1)
CHROMEDRIVER_VERSION=$(curl -sS https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$CHROME_VERSION)
wget -q -O chromedriver.zip https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip
unzip chromedriver.zip
chmod +x chromedriver
mv -f chromedriver /usr/local/bin/chromedriver

# Verificar instalación
google-chrome --version
chromedriver --version

echo "✅ Google Chrome y Chromedriver instalados correctamente."

# Iniciar la aplicación
exec uvicorn main:app --host 0.0.0.0 --port 8000
