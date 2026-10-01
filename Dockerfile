FROM python:3.12-slim

WORKDIR /app

# Prevenir generación de archivos .pyc y forzar salida inmediata en stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Instalar dependencias en una capa independiente para aprovechar la caché de Docker
COPY app/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copiar el código fuente y las plantillas de idioma
COPY app/ /app/

# Volumen persistente para datos (state.json, tokens, custom_phrases.json)
VOLUME ["/data"]

# Comprobación de salud interna: verifica que el estado exista y el proceso responda
HEALTHCHECK --interval=10m --timeout=10s --retries=3 --start-period=2m \
  CMD python -c "import os, sys; sys.exit(0 if os.path.exists('/data/state.json') else 1)"

CMD ["python", "-u", "main.py"]
