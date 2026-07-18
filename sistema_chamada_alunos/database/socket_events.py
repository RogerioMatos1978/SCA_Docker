"""
Handlers de Socket.IO.

Importante: eventos Socket.IO não passam pelo decorator
login_required das rotas HTTP normais — por isso esta é a única outra
camada (além de routes/) que grava no banco, e sempre delegando a
lógica para database/services.py, nunca com SQL direto aqui.

Padrão de tempo real usado no projeto: "broadcast + filtro no
cliente" — o servidor manda o evento aluno_chamado para TODAS as
telas conectadas (não usamos "rooms" do Socket.IO); cada tela decide
em JavaScript se aquele evento é relevante para ela.
"""

from flask import request, session

from database.models import get_db
from database import services


def registrar_eventos_socket(socketio, app):

    def _conn():
        return get_db(app.config["DATABASE_PATH"])

    def _montar_payload(chamada_row):
        conn = _conn()
        try:
            destino = services.obter_config(conn, "destino_chamada", "Portaria de Saída")
        finally:
            conn.close()
        return {
            "id": chamada_row["id"],
            "aluno_id": chamada_row["aluno_id"],
            "aluno_nome": chamada_row["aluno_nome"],
            "turma": chamada_row["turma"],
            "sala_nome": chamada_row["sala_nome"],
            "foto": chamada_row["foto"],
            "tipo": chamada_row["tipo"],
            "destino_chamada": destino,
            "criado_em": chamada_row["criado_em"],
        }

    @socketio.on("connect")
    def ao_conectar():
        # Log simples de conexão (auditoria leve). Não logamos
        # 'disconnect' para não gerar ruído em logs.
        app.logger.info("Cliente Socket.IO conectado: %s", request.sid)

    @socketio.on("chamar_aluno")
    def ao_chamar_aluno(dados):
        aluno_id = (dados or {}).get("aluno_id")
        if not aluno_id:
            socketio.emit("erro_chamada", {"mensagem": "Aluno inválido."}, to=request.sid)
            return

        usuario_id = session.get("usuario_id")
        conn = _conn()
        try:
            chamada = services.chamar_aluno(conn, aluno_id, usuario_id=usuario_id)
        finally:
            conn.close()

        if not chamada:
            socketio.emit(
                "erro_chamada",
                {"mensagem": "Não foi possível chamar este aluno (inativo ou inexistente)."},
                to=request.sid,
            )
            return

        socketio.emit("aluno_chamado", _montar_payload(chamada))
        socketio.emit("dados_atualizados", {"tipo": "chamada"})

    @socketio.on("rechamar_aluno")
    def ao_rechamar_aluno(dados):
        aluno_id = (dados or {}).get("aluno_id")
        if not aluno_id:
            socketio.emit("erro_chamada", {"mensagem": "Aluno inválido."}, to=request.sid)
            return

        usuario_id = session.get("usuario_id")
        conn = _conn()
        try:
            chamada = services.rechamar_aluno(conn, aluno_id, usuario_id=usuario_id)
        finally:
            conn.close()

        if not chamada:
            socketio.emit(
                "erro_chamada",
                {"mensagem": "Não foi possível rechamar este aluno."},
                to=request.sid,
            )
            return

        socketio.emit("aluno_chamado", _montar_payload(chamada))
