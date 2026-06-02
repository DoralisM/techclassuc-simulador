FROM python:3.10-slim

# Librerías del sistema que necesita matplotlib para generar PNG
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpng-dev \
    libfreetype6-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Crear carpeta de gráficas para que exista en el contenedor
RUN mkdir -p graficas

EXPOSE 10000

# Gunicorn con timeout extendido porque la simulación tarda al arrancar
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "--timeout", "180", "--workers", "1", "web_service:app"]
