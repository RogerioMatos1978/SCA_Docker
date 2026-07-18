"""
Área administrativa: dashboard, salas, alunos (+ importação CSV),
usuários e configurações.

Regras de permissão (ver PROMPT.md):
- administrador e supervisor: cadastro completo de salas/alunos e
  importação CSV.
- operador: só pode, nas telas de gestão do Kiosk (routes/kiosk.py),
  ativar/desativar aluno, marcar presença/falta e trocar fotos —
  nunca o cadastro completo, por isso ele nem vê os links deste
  blueprint no menu (a maioria das rotas abaixo exige supervisor+).
- só administrador acessa Usuários e Configurações.
"""

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash,
    current_app, send_from_directory,
)

from database.models import get_db
from database import services
from routes.auth import login_required, perfil_required

admin_bp = Blueprint("admin", __name__)


def _conn():
    return get_db(current_app.config["DATABASE_PATH"])


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@admin_bp.route("/")
@login_required
def dashboard():
    conn = _conn()
    try:
        stats = services.estatisticas_dashboard(conn)
        ultimas = services.ultimos_chamados(conn, limite=5)
        salas = services.listar_salas(conn)
    finally:
        conn.close()
    return render_template("admin/dashboard.html", stats=stats, ultimas=ultimas, salas=salas)


# ---------------------------------------------------------------------------
# Salas
# ---------------------------------------------------------------------------

@admin_bp.route("/salas")
@login_required
def salas():
    conn = _conn()
    try:
        lista = services.listar_salas(conn)
    finally:
        conn.close()
    return render_template("admin/salas.html", salas=lista)


@admin_bp.route("/salas/nova", methods=["GET", "POST"])
@perfil_required("administrador", "supervisor")
def salas_nova():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        cor = request.form.get("cor", "#2563eb")
        ordem = int(request.form.get("ordem") or 0)
        if not nome:
            flash("Informe o nome da sala.", "erro")
            return render_template("admin/sala_form.html", sala=None)
        conn = _conn()
        try:
            sala_id = services.criar_sala(conn, nome, cor, ordem)
            arquivo = request.files.get("foto")
            if arquivo and arquivo.filename:
                nome_arquivo = services.salvar_foto(arquivo, current_app.config["SALAS_DIR"])
                services.definir_foto_sala(conn, sala_id, nome_arquivo)
        finally:
            conn.close()
        flash("Sala criada com sucesso.", "sucesso")
        return redirect(url_for("admin.salas"))
    return render_template("admin/sala_form.html", sala=None)


@admin_bp.route("/salas/<int:sala_id>/editar", methods=["GET", "POST"])
@perfil_required("administrador", "supervisor")
def salas_editar(sala_id):
    conn = _conn()
    try:
        sala = services.buscar_sala(conn, sala_id)
        if not sala:
            conn.close()
            flash("Sala não encontrada.", "erro")
            return redirect(url_for("admin.salas"))

        if request.method == "POST":
            nome = request.form.get("nome", "").strip()
            cor = request.form.get("cor", "#2563eb")
            ordem = int(request.form.get("ordem") or 0)
            ativa = request.form.get("ativa") == "on"
            services.atualizar_sala(conn, sala_id, nome, cor, ordem, ativa)
            arquivo = request.files.get("foto")
            if arquivo and arquivo.filename:
                nome_arquivo = services.salvar_foto(arquivo, current_app.config["SALAS_DIR"])
                services.definir_foto_sala(conn, sala_id, nome_arquivo)
            flash("Sala atualizada.", "sucesso")
            return redirect(url_for("admin.salas"))
    finally:
        conn.close()
    return render_template("admin/sala_form.html", sala=sala)


@admin_bp.route("/salas/<int:sala_id>/excluir", methods=["POST"])
@perfil_required("administrador", "supervisor")
def salas_excluir(sala_id):
    conn = _conn()
    try:
        services.excluir_sala(conn, sala_id)
    finally:
        conn.close()
    flash("Sala excluída.", "sucesso")
    return redirect(url_for("admin.salas"))


@admin_bp.route("/salas/importar", methods=["GET", "POST"])
@perfil_required("administrador", "supervisor")
def salas_importar():
    if request.method == "POST":
        arquivo = request.files.get("arquivo_csv")
        if not arquivo or not arquivo.filename:
            flash("Selecione um arquivo CSV.", "erro")
            return render_template("admin/salas.html", salas=[], importar=True)
        conteudo = arquivo.stream.read().decode("utf-8", errors="ignore")
        conn = _conn()
        try:
            criadas, ignoradas = services.importar_salas_csv(conn, conteudo)
        finally:
            conn.close()
        flash(f"{criadas} sala(s) importada(s), {ignoradas} ignorada(s) (já existiam).", "sucesso")
        return redirect(url_for("admin.salas"))
    return redirect(url_for("admin.salas"))


# ---------------------------------------------------------------------------
# Alunos
# ---------------------------------------------------------------------------

@admin_bp.route("/alunos")
@login_required
def alunos():
    busca = request.args.get("busca", "").strip() or None
    sala_id = request.args.get("sala_id", type=int)
    conn = _conn()
    try:
        lista = services.listar_alunos(conn, sala_id=sala_id, busca=busca)
        salas = services.listar_salas(conn)
    finally:
        conn.close()
    return render_template("admin/alunos.html", alunos=lista, salas=salas, busca=busca or "", sala_id=sala_id)


@admin_bp.route("/alunos/novo", methods=["GET", "POST"])
@perfil_required("administrador", "supervisor")
def alunos_novo():
    conn = _conn()
    try:
        salas = services.listar_salas(conn, apenas_ativas=True)
        if request.method == "POST":
            nome = request.form.get("nome", "").strip()
            turma = request.form.get("turma", "").strip()
            sala_id = request.form.get("sala_id", type=int)
            codigo = request.form.get("codigo", "").strip() or None
            prioridade = request.form.get("prioridade") == "on"
            if not nome:
                flash("Informe o nome do aluno.", "erro")
                return render_template("admin/aluno_form.html", aluno=None, salas=salas)
            aluno_id = services.criar_aluno(conn, nome, turma, sala_id, codigo, prioridade)
            arquivo = request.files.get("foto")
            if arquivo and arquivo.filename:
                nome_arquivo = services.salvar_foto(arquivo, current_app.config["FOTOS_DIR"])
                services.definir_foto_aluno(conn, aluno_id, nome_arquivo)
            flash("Aluno cadastrado com sucesso.", "sucesso")
            return redirect(url_for("admin.alunos"))
    finally:
        conn.close()
    return render_template("admin/aluno_form.html", aluno=None, salas=salas)


@admin_bp.route("/alunos/<int:aluno_id>/editar", methods=["GET", "POST"])
@perfil_required("administrador", "supervisor")
def alunos_editar(aluno_id):
    conn = _conn()
    try:
        aluno = services.buscar_aluno(conn, aluno_id)
        salas = services.listar_salas(conn, apenas_ativas=True)
        if not aluno:
            flash("Aluno não encontrado.", "erro")
            return redirect(url_for("admin.alunos"))

        if request.method == "POST":
            nome = request.form.get("nome", "").strip()
            turma = request.form.get("turma", "").strip()
            sala_id = request.form.get("sala_id", type=int)
            codigo = request.form.get("codigo", "").strip() or None
            prioridade = request.form.get("prioridade") == "on"
            services.atualizar_aluno(conn, aluno_id, nome, turma, sala_id, codigo, prioridade)
            arquivo = request.files.get("foto")
            if arquivo and arquivo.filename:
                nome_arquivo = services.salvar_foto(arquivo, current_app.config["FOTOS_DIR"])
                services.definir_foto_aluno(conn, aluno_id, nome_arquivo)
            flash("Aluno atualizado.", "sucesso")
            return redirect(url_for("admin.alunos"))
    finally:
        conn.close()
    return render_template("admin/aluno_form.html", aluno=aluno, salas=salas)


@admin_bp.route("/alunos/<int:aluno_id>/ativo", methods=["POST"])
@login_required
def alunos_alternar_ativo(aluno_id):
    conn = _conn()
    try:
        services.alternar_ativo_aluno(conn, aluno_id)
    finally:
        conn.close()
    flash("Status do aluno atualizado.", "sucesso")
    return redirect(request.referrer or url_for("admin.alunos"))


@admin_bp.route("/alunos/<int:aluno_id>/excluir", methods=["POST"])
@perfil_required("administrador", "supervisor")
def alunos_excluir(aluno_id):
    conn = _conn()
    try:
        services.excluir_aluno(conn, aluno_id)
    finally:
        conn.close()
    flash("Aluno excluído.", "sucesso")
    return redirect(url_for("admin.alunos"))


@admin_bp.route("/alunos/importar", methods=["GET", "POST"])
@perfil_required("administrador", "supervisor")
def alunos_importar():
    if request.method == "POST":
        arquivo = request.files.get("arquivo_csv")
        if not arquivo or not arquivo.filename:
            flash("Selecione um arquivo CSV.", "erro")
            return redirect(url_for("admin.alunos_importar"))
        conteudo = arquivo.stream.read().decode("utf-8", errors="ignore")
        conn = _conn()
        try:
            criados, ignorados = services.importar_alunos_csv(conn, conteudo)
        finally:
            conn.close()
        flash(f"{criados} aluno(s) importado(s), {ignorados} ignorado(s) (código duplicado).", "sucesso")
        return redirect(url_for("admin.alunos"))
    return render_template("admin/alunos_importar.html")


# ---------------------------------------------------------------------------
# Usuários (só administrador)
# ---------------------------------------------------------------------------

@admin_bp.route("/usuarios", methods=["GET", "POST"])
@perfil_required("administrador")
def usuarios():
    conn = _conn()
    try:
        if request.method == "POST":
            nome = request.form.get("nome", "").strip()
            email = request.form.get("email", "").strip().lower()
            senha = request.form.get("senha", "")
            perfil = request.form.get("perfil", "operador")
            if not nome or not email or len(senha) < 6:
                flash("Preencha nome, e-mail e uma senha com pelo menos 6 caracteres.", "erro")
            elif services.buscar_usuario_por_email(conn, email):
                flash("Já existe um usuário com esse e-mail.", "erro")
            else:
                services.criar_usuario(conn, nome, email, senha, perfil)
                flash("Usuário criado com sucesso.", "sucesso")
            return redirect(url_for("admin.usuarios"))

        lista = services.listar_usuarios(conn)
    finally:
        conn.close()
    return render_template("admin/usuarios.html", usuarios=lista)


@admin_bp.route("/usuarios/<int:usuario_id>/ativo", methods=["POST"])
@perfil_required("administrador")
def usuarios_alternar_ativo(usuario_id):
    conn = _conn()
    try:
        services.alternar_ativo_usuario(conn, usuario_id)
    finally:
        conn.close()
    flash("Status do usuário atualizado.", "sucesso")
    return redirect(url_for("admin.usuarios"))


# ---------------------------------------------------------------------------
# Configurações (só administrador)
# ---------------------------------------------------------------------------

@admin_bp.route("/configuracoes", methods=["GET", "POST"])
@perfil_required("administrador")
def configuracoes():
    conn = _conn()
    try:
        if request.method == "POST":
            services.definir_config(conn, "nome_instituicao", request.form.get("nome_instituicao", "").strip())
            services.definir_config(conn, "destino_chamada", request.form.get("destino_chamada", "").strip())
            services.definir_config(
                conn, "kiosk_modo_simplificado",
                "1" if request.form.get("kiosk_modo_simplificado") == "on" else "0",
            )
            flash("Configurações salvas.", "sucesso")
            return redirect(url_for("admin.configuracoes"))

        configs = services.obter_todas_configs(conn)
    finally:
        conn.close()
    return render_template("admin/configuracoes.html", configs=configs)


# ---------------------------------------------------------------------------
# Fotos (servidas das pastas configuráveis, fora de static/ padrão)
# ---------------------------------------------------------------------------

@admin_bp.route("/fotos/<path:nome_arquivo>")
def servir_foto_aluno(nome_arquivo):
    return send_from_directory(current_app.config["FOTOS_DIR"], nome_arquivo)


@admin_bp.route("/fotos-salas/<path:nome_arquivo>")
def servir_foto_sala(nome_arquivo):
    return send_from_directory(current_app.config["SALAS_DIR"], nome_arquivo)
