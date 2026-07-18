"""
Screen: painel(is) de TV. Todas as rotas são PÚBLICAS — pensadas para
abrir sozinhas em TVs/terminais físicos.

Roteamento por sala: o servidor sempre faz broadcast do evento
aluno_chamado para TODAS as telas (sem "rooms" do Socket.IO). Cada TV
decide em JavaScript (static/js/screen.js) se deve reagir, comparando
chamada.sala_nome com o nome da própria sala (injetado aqui via
CONFIG.salaNome). /screen/geral não define salaNome e reage a tudo.

Auto-pareamento sala↔TV: feito com localStorage no navegador da
própria TV (não no servidor) — ver static/js/screen_selecionar.js.
"""

from flask import Blueprint, render_template, current_app, abort

from database.models import get_db
from database import services

screen_bp = Blueprint("screen", __name__)


def _conn():
    return get_db(current_app.config["DATABASE_PATH"])


@screen_bp.route("/")
def selecionar():
    """Grade de salas para a TV escolher (na primeira vez que abre).
    Depois de escolhida, o JS salva no localStorage e navega direto
    para /screen/<sala_id> nas próximas vezes."""
    conn = _conn()
    try:
        salas = services.listar_salas(conn, apenas_ativas=True)
    finally:
        conn.close()
    return render_template("screen/selecionar.html", salas=salas)


@screen_bp.route("/geral")
def geral():
    """TV 'geral': reage a chamadas de qualquer sala (sem filtro)."""
    conn = _conn()
    try:
        destino = services.obter_config(conn, "destino_chamada", "Portaria de Saída")
        recentes = services.ultimos_chamados(conn, limite=3)
    finally:
        conn.close()
    return render_template(
        "screen/tela.html", sala=None, destino_chamada=destino, recentes=recentes,
    )


@screen_bp.route("/<int:sala_id>")
def tela_sala(sala_id):
    """TV dedicada a uma sala específica: só reage a chamadas cujo
    aluno pertence a essa sala."""
    conn = _conn()
    try:
        sala = services.buscar_sala(conn, sala_id)
        if not sala:
            conn.close()
            abort(404)
        destino = services.obter_config(conn, "destino_chamada", "Portaria de Saída")
        recentes = services.ultimos_chamados(conn, limite=3)
    finally:
        conn.close()
    return render_template(
        "screen/tela.html", sala=sala, destino_chamada=destino, recentes=recentes,
    )
