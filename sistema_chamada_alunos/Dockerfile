# Imagem base enxuta com Python 3.12. Usamos 3.12 em vez de 3.13
# porque algumas dependências (eventlet/greenlet, Pillow) ainda não
# publicam "wheels" pré-compiladas para 3.13 em todas as versões,
# o que obriga a compilar do zero dentro do container (e falha sem
# um compilador C instalado). 3.12 tem cobertura de wheels madura.
FROM python:3.12-slim

# Evita que o Python gere arquivos .pyc e deixa o log aparecer na hora
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production

WORKDIR /app

# Instala as dependências primeiro (aproveita cache do Docker enquanto
# o código muda, mas o requirements.txt não muda)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o resto do código da aplicação
COPY . .

# Garante que as pastas usadas para dados persistentes existam
RUN mkdir -p database static/fotos static/fotos_salas static/uploads backups logs

EXPOSE 5000

# Healthcheck simples: o Docker Desktop mostra "healthy"/"unhealthy"
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/healthcheck')" || exit 1

CMD ["python", "app.py"]
