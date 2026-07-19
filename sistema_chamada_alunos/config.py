"""
Configuração da aplicação.

Existem duas classes de configuração (Development e Production) que
herdam de Config. Qual delas é usada é decidido pela variável de
ambiente FLASK_ENV (ver app.py).

Todos os caminhos de pastas (banco de dados, fotos, backups, logs) são
lidos de variáveis de ambiente quando existem, para funcionar tanto
rodando direto no computador quanto dentro de um container Docker
(onde essas pastas normalmente são "volumes" montados do host).
"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _env_bool(nome, padrao):
    valor = os.environ.get(nome)
    if valor is None:
        return padrao
    return valor.strip().lower() in ("1", "true", "sim", "yes", "on")


class Config:
    # Chave usada para assinar a sessão do Flask e os tokens CSRF.
    # Em produção, defina SECRET_KEY como variável de ambiente com um
    # valor aleatório e difícil de adivinhar.
    SECRET_KEY = os.environ.get("SECRET_KEY", "troque-esta-chave-em-producao")

    # Banco de dados SQLite (arquivo único).
    DATABASE_PATH = os.environ.get(
        "DATABASE_PATH", os.path.join(BASE_DIR, "database", "alunos.db")
    )

    # Pastas de arquivos enviados pelo usuário (fotos) e backups/logs.
    FOTOS_DIR = os.environ.get(
        "FOTOS_DIR", os.path.join(BASE_DIR, "static", "fotos")
    )
    SALAS_DIR = os.environ.get(
        "SALAS_DIR", os.path.join(BASE_DIR, "static", "fotos_salas")
    )
    UPLOADS_DIR = os.environ.get(
        "UPLOADS_DIR", os.path.join(BASE_DIR, "static", "uploads")
    )
    BACKUPS_DIR = os.environ.get(
        "BACKUPS_DIR", os.path.join(BASE_DIR, "backups")
    )
    LOGS_DIR = os.environ.get(
        "LOGS_DIR", os.path.join(BASE_DIR, "logs")
    )

    # Pasta com os CSVs de exemplo (salas_exemplo.csv, alunos_exemplo.csv)
    # usados para deixar o sistema pronto pra testar assim que ele sobe
    # pela primeira vez. Ver AUTO_IMPORTAR_EXEMPLOS abaixo.
    EXEMPLOS_DIR = os.environ.get(
        "EXEMPLOS_DIR", os.path.join(BASE_DIR, "exemplos")
    )

    # Se True (padrão), na primeira vez que o sistema roda com o banco
    # de salas vazio, importa automaticamente os CSVs de exemplo — o
    # Kiosk e a TV já sobem com salas/alunos de teste, sem precisar
    # importar nada manualmente. Para desligar (ex.: instalação real
    # de uma escola, sem dados fictícios), defina a variável de
    # ambiente AUTO_IMPORTAR_EXEMPLOS=0 no docker-compose.yml.
    AUTO_IMPORTAR_EXEMPLOS = _env_bool("AUTO_IMPORTAR_EXEMPLOS", True)

    # Tamanho máximo de upload (5 MB) — evita que alguém envie um
    # arquivo gigante sem querer.
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024

    # Extensões de imagem aceitas para foto de aluno/sala.
    EXTENSOES_IMAGEM_PERMITIDAS = {"png", "jpg", "jpeg", "webp"}

    # Nome do cookie de sessão.
    SESSION_COOKIE_NAME = "chamada_alunos_session"

    WTF_CSRF_ENABLED = True


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


CONFIG_POR_AMBIENTE = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
