FROM python:3.12-slim

# Instalar solo lo necesario del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium libnss3 libatk1.0-0 libatk-bridge2.0-0 libdrm2 \
    libxkbcommon0 libxcb1 libxcomposite1 libxdamage1 libxrandr2 libgbm1 \
    libgtk-3-0 libpangocairo-1.0-0 libpango-1.0-0 libatspi2.0-0 \
    libxss1 fonts-liberation ca-certificates unzip \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Instalar solo Playwright + Chromium
RUN pip install --upgrade pip 

# && pip install playwright && \
#     playwright install chromium

# Crear y usar un directorio limpio
WORKDIR /app

# Copiar primero solo los requirements para cachear pip install
COPY requirements.txt .

# Instalar solo las dependencias necesarias
RUN pip install --no-cache-dir -r requirements.txt


# Copiar el resto del proyecto
COPY . .

# Variables de entorno
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=benchmark_django.settings

# Puerto expuesto
EXPOSE 8000

RUN python manage.py collectstatic --noinput

# Comando final
CMD ["gunicorn", "-b", "0.0.0.0:8000", "benchmark_django.wsgi:application"]
