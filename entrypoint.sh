#!/bin/bash

echo "🔹 Instalando dependencias necesarias para Chrome y Chromedriver..."
apt-get update && apt-get install -y \
    libglib2.0-0 \
    libnss3 \
    libgconf-2-4 \
    libfontconfig1 \
    libx11-xcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxi6 \
    libxtst6 \
    libxrandr2 \
    libasound2 \
    libpango1.0-0 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libgtk-3-0

echo "✅ Dependencias de Chrome y Chromedriver instaladas."

# Iniciar la aplicación
exec uvicorn main:app --host 0.0.0.0 --port 8000
