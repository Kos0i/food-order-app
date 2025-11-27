# Development stage for testing
FROM python:3.9-slim as development

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-test.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-test.txt

COPY . .

EXPOSE 8000

CMD ["python", "app.py"]