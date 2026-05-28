FROM python:3.11-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pirlib/ pirlib/
COPY models/ models/

COPY consumer.py .
COPY producer.py .
COPY logger.py .

COPY virtual_sensor_rules.py .
COPY virtual_sensor_ml.py .
COPY virtual_sensor_combiner.py .

COPY api.py .