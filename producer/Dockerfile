FROM python:3.11

WORKDIR /app

# Install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy producer code
COPY producer /app/producer

ENV PYTHONUNBUFFERED=1

CMD ["python", "producer/main.py"]
