"""
Ponto de entrada da aplicação.

Usa o padrão "application factory" (create_app): a função monta e
devolve o app Flask + a instância do socketio, em vez de criar tudo
direto no nível do módulo. Isso facilita testes automatizados (cada
teste pode criar sua própria instância isolada) e deixar claro onde
cada peça é montada.

IMPORTANTE: o monkey_patch do eventlet precisa rodar antes de
qualquer outro import que use sockets/threads (Flask incluso), senão
o Socket.IO não funciona direito. Por isso ele é a primeiríssima
coisa deste arquivo.
"""

import eventlet
eventlet.monkey_patch()

import os
import logging

from flask import Flask, render_template, jsonify, session
from flask_socketio import SocketIO
from flask_wtf import CSRFProtect

from config import CONFIG_POR_AMBIENTE
from database.models import init_db, get_db
from database import services
from database.socket_events import registrar_eventos_socket

socketio = SocketIO(cors_allowed_origins="*")
csrf = CSRFProtect()


def create_app(config_name=None):
    config_name = config_name or os.environ.get("FLASK_ENV", "production")
    app = Flask(__name__)
    app.config.from_object(CONFIG_POR_AMBIENTE.get(config_name, CONFIG_POR_AMBIENTE["production"]))

    logging.basicConfig(level=logging.INFO)

    # Garante que as pastas de dados existam (útil tanto local quanto
    # em Docker, onde elas normalmente são volumes montados do host).
    for pasta in (
        app.config["FOTOS_DIR"],
        app.config["SALAS_DIR"],
        app.config["UPLOADS_DIR"],
        app.config["BACKUPS_DIR"],
        app.config["LOGS_DIR"],
    ):
        os.makedirs(pasta, exist_ok=True)

    init_db(app.config["DATABASE_PATH"])

    conn = get_db(app.config["DATABASE_PATH"])
    try:
        # Cria um administrador padrão na primeiríssima execução, se
        # ainda não existir nenhum usuário no banco.
        credenciais_iniciais = services.criar_usuario_padrao_se_nao_existir(conn)

        # Deixa o sistema pronto pra testar assim que ele sobe: se
        # ainda não há nenhuma sala cadastrada, importa os CSVs de
        # exemplo (salas/alunos com as disciplinas da BNCC) — assim o
        # Kiosk e a TV já têm o que mostrar logo no primeiro
        # "docker compose up". Só roda se AUTO_IMPORTAR_EXEMPLOS
        # estiver ligado (padrão) e nunca sobrescreve dados já
        # existentes (ver services.importar_exemplos_iniciais).
        resumo_exemplos = None
        if app.config.get("AUTO_IMPORTAR_EXEMPLOS", True):
            resumo_exemplos = services.importar_exemplos_iniciais(
                conn, app.config["EXEMPLOS_DIR"]
            )
    finally:
        conn.close()

    if credenciais_iniciais:
        app.logger.warning(
            "Usuário administrador padrão criado: usuario=%s senha=%s "
            "(troque a senha assim que possível em /admin/usuarios)",
            credenciais_iniciais["usuario"], credenciais_iniciais["senha"],
        )
    if resumo_exemplos:
        app.logger.warning(
            "Dados de exemplo importados automaticamente: %s sala(s), %s aluno(s) "
            "(pasta exemplos/ — desligue com AUTO_IMPORTAR_EXEMPLOS=0 se não quiser isso).",
            resumo_exemplos["salas_criadas"], resumo_exemplos["alunos_criados"],
        )

    csrf.init_app(app)
    socketio.init_app(app, async_mode="eventlet")
    registrar_eventos_socket(socketio, app)

    # Blueprints — cada área do sistema é um blueprint próprio.
    from routes.auth import auth_bp
    from routes.admin import admin_bp
    from routes.kiosk import kiosk_bp
    from routes.screen import screen_bp
    from routes.presenca import presenca_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(kiosk_bp, url_prefix="/kiosk")
    app.register_blueprint(screen_bp, url_prefix="/screen")
    app.register_blueprint(presenca_bp, url_prefix="/presenca")

    csrf.exempt(kiosk_bp)  # fila/gestão do kiosk usa formulários simples via fetch/JS

    @app.route("/")
    def home():
        """Home pública: convida para o login quem não está logado, e
        dá acesso rápido ao Kiosk/Screen (ambos públicos) e ao painel
        para quem já está logado."""
        usuario_id = session.get("usuario_id")
        usuario = None
        if usuario_id:
            conn = get_db(app.config["DATABASE_PATH"])
            try:
                usuario = services.buscar_usuario_por_id(conn, usuario_id)
            finally:
                conn.close()
            if not usuario or not usuario["ativo"]:
                session.clear()
                usuario = None
        return render_template("home.html", usuario=usuario)

    @app.route("/healthcheck")
    def healthcheck():
        return jsonify({"status": "ok"})

    return app


app = create_app()

if __name__ == "__main__":
    porta = int(os.environ.get("PORT", 5000))
    # host="0.0.0.0": aceita conexões de qualquer dispositivo na rede
    # local (não só do próprio computador), necessário para o Kiosk e
    # as TVs abrirem em outros aparelhos.
    socketio.run(app, host="0.0.0.0", port=porta)
