FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY pirlib/ pirlib/
COPY models/ models/
COPY consumer.py .
COPY producer.py .
COPY logger.py .