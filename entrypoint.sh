#!/bin/bash

echo "🔹 Instalando dependencias necesarias para Chrome y Chromedriver..."
apt-get update && apt-get install -y wget unzip curl

# Instalar Google Chrome
echo "🔹 Instalando Google Chrome..."
wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
dpkg -i google-chrome-stable_current_amd64.deb || apt-get install -fy

# Instalar Chromedriver
echo "🔹 Instalando Chromedriver..."
CHROMEDRIVER_VERSION=$(curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE)
wget -q "https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip"
unzip chromedriver_linux64.zip
mv chromedriver /usr/local/bin/
chmod +x /usr/local/bin/chromedriver

echo "✅ Google Chrome y Chromedriver instalados correctamente."

# Iniciar la aplicación
exec uvicorn main:app --host 0.0.0.0 --port 8000

