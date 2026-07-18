"""
Painel de presença diária — exige login (qualquer perfil).

Regra de negócio: a ausência de registro em 'presencas' para um aluno
num dia = presente por padrão. Só é preciso marcar quem faltou; não é
necessário confirmar presença de todo mundo todo dia. Um aluno
marcado como 'faltante' hoje some da fila do Kiosk automaticamente.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app

from database.models import get_db
from database import services
from routes.auth import login_required

presenca_bp = Blueprint("presenca", __name__)


def _conn():
    return get_db(current_app.config["DATABASE_PATH"])


@presenca_bp.route("/")
@login_required
def index():
    sala_id = request.args.get("sala_id", type=int)
    conn = _conn()
    try:
        alunos = services.listar_alunos_com_presenca_hoje(conn, sala_id=sala_id)
        salas = services.listar_salas(conn, apenas_ativas=True)
    finally:
        conn.close()
    return render_template("presenca/index.html", alunos=alunos, salas=salas, sala_id=sala_id)


@presenca_bp.route("/marcar", methods=["POST"])
@login_required
def marcar():
    aluno_id = request.form.get("aluno_id", type=int)
    status = request.form.get("status")
    if status not in ("presente", "faltante"):
        flash("Status inválido.", "erro")
        return redirect(request.referrer or url_for("presenca.index"))

    conn = _conn()
    try:
        services.marcar_presenca(conn, aluno_id, status, usuario_id=request.usuario_logado["id"])
    finally:
        conn.close()
    flash("Presença atualizada.", "sucesso")
    return redirect(request.referrer or url_for("presenca.index"))
