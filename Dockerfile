# Usa una imagen de Python como base
FROM python:3.10

# Configurar el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar los archivos del proyecto al contenedor
COPY . .

# Instalar las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Dar permisos de ejecución al script de inicio
RUN chmod +x entrypoint.sh

# Definir el entrypoint
ENTRYPOINT ["/bin/bash", "./entrypoint.sh"]

