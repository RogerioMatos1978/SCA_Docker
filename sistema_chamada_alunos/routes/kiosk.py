"""
Kiosk: terminal de chamada.

A fila (/kiosk/) é PÚBLICA de propósito — pensada para rodar sozinha
num terminal fixo na portaria, sem alguém precisar logar toda vez. A
chamada em si acontece via Socket.IO (evento chamar_aluno/rechamar_aluno,
ver database/socket_events.py e static/js/kiosk.js), não por um POST
HTTP tradicional.

/kiosk/gestao/* exige login — mudanças de cadastro (ativar/desativar
aluno, trocar foto) continuam exigindo autenticação mesmo com o
terminal público.
"""

from collections import Counter

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash,
    current_app,
)

from database.models import get_db
from database import services
from routes.auth import login_required

kiosk_bp = Blueprint("kiosk", __name__)


def _conn():
    return get_db(current_app.config["DATABASE_PATH"])


@kiosk_bp.route("/")
def fila():
    """Tela pública do terminal: grade de cards com os alunos que
    podem ser chamados agora (+ últimos chamados) e um menu de salas
    para filtrar por matéria/sala — pensado para toque em TV/tablet.
    A chamada em si é feita via Socket.IO pelo static/js/kiosk.js."""
    conn = _conn()
    try:
        alunos = services.fila_kiosk(conn)
        recentes = services.ultimos_chamados(conn, limite=5)
        modo_simplificado = services.obter_config(conn, "kiosk_modo_simplificado", "0") == "1"
        salas = services.listar_salas(conn, apenas_ativas=True)
    finally:
        conn.close()
    contagem_por_sala = Counter(a["sala_nome"] for a in alunos if a["sala_nome"])
    return render_template(
        "kiosk/fila.html",
        alunos=alunos,
        recentes=recentes,
        modo_simplificado=modo_simplificado,
        salas=salas,
        contagem_por_sala=contagem_por_sala,
    )


@kiosk_bp.route("/gestao")
@login_required
def gestao():
    """Tela de gestão do dia a dia (login obrigatório). Qualquer
    perfil logado pode ativar/desativar aluno e trocar a foto por
    aqui — cadastro completo continua só em /admin."""
    busca = request.args.get("busca", "").strip() or None
    conn = _conn()
    try:
        alunos = services.listar_alunos(conn, busca=busca)
    finally:
        conn.close()
    return render_template("kiosk/gestao.html", alunos=alunos, busca=busca or "")


@kiosk_bp.route("/gestao/aluno/<int:aluno_id>/foto", methods=["POST"])
@login_required
def gestao_aluno_foto(aluno_id):
    arquivo = request.files.get("foto")
    if not arquivo or not arquivo.filename:
        flash("Selecione uma foto.", "erro")
        return redirect(request.referrer or url_for("kiosk.gestao"))
    conn = _conn()
    try:
        nome_arquivo = services.salvar_foto(arquivo, current_app.config["FOTOS_DIR"])
        services.definir_foto_aluno(conn, aluno_id, nome_arquivo)
    finally:
        conn.close()
    flash("Foto atualizada.", "sucesso")
    return redirect(request.referrer or url_for("kiosk.gestao"))


@kiosk_bp.route("/gestao/aluno/<int:aluno_id>/resetar", methods=["POST"])
@login_required
def gestao_resetar_status(aluno_id):
    """Volta um aluno chamado por engano para 'aguardando'."""
    conn = _conn()
    try:
        services.resetar_status_aluno(conn, aluno_id)
    finally:
        conn.close()
    flash("Aluno voltou para a fila de espera.", "sucesso")
    return redirect(request.referrer or url_for("kiosk.gestao"))
