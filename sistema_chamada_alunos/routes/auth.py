"""
Autenticação: login/logout, e os decorators login_required e
perfil_required usados pelas outras rotas.

Regra importante (evita o bug de "sessão fantasma"): login_required
não confia só na presença de session['usuario_id'] — ele revalida no
banco, a cada acesso, que aquele usuário ainda existe e está ativo.
Se a conta foi excluída/desativada enquanto o navegador continuava
logado (ex.: terminal do Kiosk esquecido logado), a sessão é encerrada
de forma limpa, com mensagem amigável, em vez de deixar a aplicação
quebrar mais adiante numa gravação com FK inválida.
"""

from functools import wraps

from flask import (
    Blueprint, render_template, request, redirect, url_for, session, flash,
    current_app,
)

from database.models import get_db
from database import services

auth_bp = Blueprint("auth", __name__)


def _usuario_logado_valido():
    usuario_id = session.get("usuario_id")
    if not usuario_id:
        return None
    conn = get_db(current_app.config["DATABASE_PATH"])
    try:
        usuario = services.buscar_usuario_por_id(conn, usuario_id)
    finally:
        conn.close()
    if not usuario or not usuario["ativo"]:
        return None
    return usuario


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        usuario = _usuario_logado_valido()
        if not usuario:
            session.clear()
            flash("Sua sessão expirou ou sua conta foi desativada. Faça login novamente.", "aviso")
            return redirect(url_for("auth.login", proximo=request.path))
        # Deixa o usuário logado disponível para a view sem precisar
        # buscar de novo.
        request.usuario_logado = usuario
        return view_func(*args, **kwargs)

    return wrapper


def perfil_required(*perfis_permitidos):
    """Uso: @perfil_required('administrador', 'supervisor')"""

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(*args, **kwargs):
            usuario = request.usuario_logado
            if usuario["perfil"] not in perfis_permitidos:
                flash("Você não tem permissão para acessar esta página.", "erro")
                return redirect(url_for("admin.dashboard"))
            return view_func(*args, **kwargs)

        return wrapper

    return decorator


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login_usuario = request.form.get("usuario", "").strip().lower()
        senha = request.form.get("senha", "")
        proximo = request.form.get("proximo") or request.args.get("proximo")

        conn = get_db(current_app.config["DATABASE_PATH"])
        try:
            usuario_row = services.buscar_usuario_por_login(conn, login_usuario)
        finally:
            conn.close()

        if not usuario_row or not usuario_row["ativo"] or not services.verificar_senha(usuario_row, senha):
            flash("Usuário ou senha inválidos.", "erro")
            return render_template("login.html", proximo=proximo)

        session.clear()
        session["usuario_id"] = usuario_row["id"]
        session["usuario_nome"] = usuario_row["nome"]
        session["usuario_perfil"] = usuario_row["perfil"]
        flash(f"Bem-vindo(a), {usuario_row['nome']}!", "sucesso")
        return redirect(proximo or url_for("admin.dashboard"))

    proximo = request.args.get("proximo")
    return render_template("login.html", proximo=proximo)


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Você saiu do sistema.", "sucesso")
    return redirect(url_for("home"))
