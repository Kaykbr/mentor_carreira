# Imagem de produção do Mentor de Carreira (deploy no Render).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependências primeiro: aproveita o cache de camadas quando só o código muda.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 10000

# 2 workers atendem ~50 alunos simultâneos com folga (o gargalo é a latência da IA, não CPU).
# --proxy-headers: o Render termina o TLS num proxy; sem isso o IP do cliente e o esquema
# https chegam errados (quebra o rate limit por IP e o cookie Secure).
# --timeout-keep-alive alto: gerações de PDI/currículo levam até ~60s.
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "10000", \
     "--workers", "2", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*", \
     "--timeout-keep-alive", "75"]
