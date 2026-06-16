# Usar una imagen oficial de Python ligera como base
FROM python:3.11-slim

# Configurar la carpeta de trabajo dentro del contenedor
WORKDIR /app

# Copiar el archivo de requerimientos primero
COPY requirements.txt .

# Instalar las librerías necesarias dentro del contenedor
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el código de nuestro bot a la carpeta /app
COPY . .

# Comando definitivo que ejecutará el bot cuando el contenedor se encienda
CMD ["python", "bot.py"]