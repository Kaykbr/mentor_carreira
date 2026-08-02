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

# 1 worker é suficiente para 50 alunos assíncronos: o app é I/O-bound (fica
# esperando a IA responder), Python usa async para muitos requests concorrentes,
# e 2 workers dobrariam o uso de RAM (~140 MB extras) sem ganho real de throughput
# no plano Starter de 512 MB. Ver README/CLAUDE.md para o raciocínio completo.
# --proxy-headers: o Render termina o TLS num proxy; sem isso o IP do cliente e o
# esquema https chegam errados (quebra o rate limit por IP e o cookie Secure).
# --timeout-keep-alive alto: gerações de PDI/currículo levam até ~60s.
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "10000", \
     "--workers", "1", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*", \
     "--timeout-keep-alive", "75"]
