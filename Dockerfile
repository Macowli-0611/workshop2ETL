# Dockerfile para entorno de Apache Airflow 3.1.8 con dependencias del proyecto
FROM apache/airflow:3.1.8-python3.11

USER root
# Instalar utilidades esenciales si se requieren para compilación ligera
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

USER airflow

# Copiar e instalar dependencias del taller (Great Expectations, Pandas, etc.)
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt
