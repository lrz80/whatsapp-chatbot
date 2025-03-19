#!/bin/bash

echo "🔹 Instalando dependencias necesarias..."
apt-get update && apt-get install -y wget unzip curl

echo "✅ Dependencias instaladas."

# Iniciar la aplicación
exec uvicorn main:app --host 0.0.0.0 --port 8000

