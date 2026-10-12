# Uma imagem só, usada pelos dois serviços (api e bot); o que muda é o comando.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependências primeiro: essa camada fica em cache enquanto o requirements.txt não mudar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
