# Apache Airflow 3.1.8 image with the project dependencies
FROM apache/airflow:3.1.8-python3.11

USER root
# Build tools needed to compile some Python dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

USER airflow

# Install the workshop dependencies (Great Expectations, pandas, etc.)
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt
