# Imagem base enxuta com Python 3.12. Usamos 3.12 em vez de 3.13
# porque algumas dependências (eventlet/greenlet, Pillow) ainda não
# publicam "wheels" pré-compiladas para 3.13 em todas as versões,
# o que obriga a compilar do zero dentro do container (e falha sem
# um compilador C instalado). 3.12 tem cobertura de wheels madura.
FROM python:3.12-slim

# Evita que o Python gere arquivos .pyc e deixa o log aparecer na hora
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    DEBIAN_FRONTEND=noninteractive \
    TZ=America/Sao_Paulo

WORKDIR /app

# Instala o fuso horário local (America/Sao_Paulo por padrão — troque o
# TZ acima e no docker-compose.yml se a escola ficar em outro fuso).
# Isso é importante porque a virada Matutino/Vespertino usa o horário
# local do container (datetime('now','localtime') no SQLite); sem isso
# o container fica em UTC e a virada de período acontece na hora errada.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# Instala as dependências primeiro (aproveita cache do Docker enquanto
# o código muda, mas o requirements.txt não muda)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o resto do código da aplicação (inclui a pasta exemplos/ com
# os CSVs de salas/alunos de teste)
COPY . .

# Garante que as pastas usadas para dados persistentes existam
RUN mkdir -p database static/fotos static/fotos_salas static/uploads backups logs

EXPOSE 5000

# Healthcheck simples: o Docker Desktop mostra "healthy"/"unhealthy"
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/healthcheck')" || exit 1

CMD ["python", "app.py"]
