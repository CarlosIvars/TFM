FROM python:3.12-slim

# 1) Paquetes del sistema necesarios para Chromium/Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    # libs frecuentes para chromium/playwright
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libdrm2 \
    libxkbcommon0 libxcb1 libxcomposite1 libxdamage1 libxrandr2 libxfixes3 libgbm1 \
    libgtk-3-0 libpangocairo-1.0-0 libpango-1.0-0 libatspi2.0-0 \
    libx11-6 libxext6 libxshmfence1 \
    libxss1 fonts-liberation ca-certificates unzip \
    libasound2 libcups2 libdbus-1-3 \
 && rm -rf /var/lib/apt/lists/*

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=benchmark_django.settings \
    # Clave: ruta global para los binarios de Playwright (build y runtime)
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

# Instala dependencias Python y Playwright
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir playwright \
 && playwright install chromium

# Copia el proyecto
COPY . .

# Recoge estáticos
RUN python manage.py collectstatic --noinput

# Usuario no root + permisos
RUN useradd -m appuser \
 && chown -R appuser:appuser /app /ms-playwright
USER appuser

EXPOSE 8000
CMD ["gunicorn", "-b", "0.0.0.0:8000", "--capture-output", "--enable-stdio-inheritance", "benchmark_django.wsgi:application"]
