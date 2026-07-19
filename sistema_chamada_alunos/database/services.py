"""
Toda a lógica de negócio e todo o SQL do sistema mora aqui.

routes/*.py NUNCA deve ter uma query SQL direta — sempre chama uma
função deste arquivo. Isso mantém as rotas simples (só HTTP) e deixa
a lógica de negócio num lugar só, fácil de testar e reaproveitar
(o socket_events.py também chama estas mesmas funções).

Convenção: nomes de função em português, um verbo por ação
(listar_, buscar_, criar_, atualizar_, excluir_, marcar_, chamar_...).
"""

import os
import uuid
import datetime
import csv
import io

from werkzeug.security import generate_password_hash, check_password_hash

try:
    from PIL import Image
except ImportError:  # Pillow é opcional só para não quebrar se faltar
    Image = None


# ---------------------------------------------------------------------------
# Usuários / autenticação
# ---------------------------------------------------------------------------

def existe_algum_usuario(conn):
    row = conn.execute("SELECT COUNT(*) AS total FROM usuarios").fetchone()
    return row["total"] > 0


def criar_usuario_padrao_se_nao_existir(conn):
    """Na primeira vez que o sistema roda (banco vazio de usuários),
    cria um administrador padrão para dar acesso inicial ao sistema.
    Credenciais: admin / admin123 — o próprio README avisa para
    trocar a senha assim que possível."""
    if existe_algum_usuario(conn):
        return None
    senha_hash = generate_password_hash("admin123")
    conn.execute(
        """INSERT INTO usuarios (nome, usuario, senha_hash, perfil, ativo)
           VALUES (?, ?, ?, 'administrador', 1)""",
        ("Administrador", "admin", senha_hash),
    )
    conn.commit()
    return {"usuario": "admin", "senha": "admin123"}


def buscar_usuario_por_login(conn, usuario):
    return conn.execute(
        "SELECT * FROM usuarios WHERE usuario = ?", (usuario,)
    ).fetchone()


def buscar_usuario_por_id(conn, usuario_id):
    return conn.execute(
        "SELECT * FROM usuarios WHERE id = ?", (usuario_id,)
    ).fetchone()


def _id_usuario_valido(conn, usuario_id):
    """Confirma que um usuario_id ainda existe e está ativo antes de
    usá-lo como FK numa gravação (chamada, presença...). Evita o bug
    de 'sessão fantasma': a conta foi excluída/desativada mas um
    dispositivo continua logado com o id antigo."""
    if not usuario_id:
        return False
    row = conn.execute(
        "SELECT id FROM usuarios WHERE id = ? AND ativo = 1", (usuario_id,)
    ).fetchone()
    return row is not None


def verificar_senha(usuario_row, senha):
    return check_password_hash(usuario_row["senha_hash"], senha)


def listar_usuarios(conn):
    return conn.execute(
        "SELECT * FROM usuarios ORDER BY nome COLLATE NOCASE"
    ).fetchall()


def criar_usuario(conn, nome, usuario, senha, perfil):
    senha_hash = generate_password_hash(senha)
    conn.execute(
        """INSERT INTO usuarios (nome, usuario, senha_hash, perfil, ativo)
           VALUES (?, ?, ?, ?, 1)""",
        (nome, usuario, senha_hash, perfil),
    )
    conn.commit()


def alternar_ativo_usuario(conn, usuario_id):
    conn.execute(
        "UPDATE usuarios SET ativo = 1 - ativo WHERE id = ?", (usuario_id,)
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Salas
# ---------------------------------------------------------------------------

def listar_salas(conn, apenas_ativas=False):
    sql = "SELECT * FROM salas"
    if apenas_ativas:
        sql += " WHERE ativa = 1"
    sql += " ORDER BY ordem, nome COLLATE NOCASE"
    return conn.execute(sql).fetchall()


def buscar_sala(conn, sala_id):
    return conn.execute("SELECT * FROM salas WHERE id = ?", (sala_id,)).fetchone()


def buscar_sala_por_nome(conn, nome):
    return conn.execute("SELECT * FROM salas WHERE nome = ?", (nome,)).fetchone()


def contar_salas(conn):
    return conn.execute("SELECT COUNT(*) AS total FROM salas").fetchone()["total"]


def criar_sala(conn, nome, cor="#2563eb", ordem=0):
    cur = conn.execute(
        "INSERT INTO salas (nome, cor, ordem, ativa) VALUES (?, ?, ?, 1)",
        (nome, cor, ordem),
    )
    conn.commit()
    return cur.lastrowid


def atualizar_sala(conn, sala_id, nome, cor, ordem, ativa):
    conn.execute(
        """UPDATE salas SET nome = ?, cor = ?, ordem = ?, ativa = ?
           WHERE id = ?""",
        (nome, cor, ordem, 1 if ativa else 0, sala_id),
    )
    conn.commit()


def excluir_sala(conn, sala_id):
    conn.execute("DELETE FROM salas WHERE id = ?", (sala_id,))
    conn.commit()


def definir_foto_sala(conn, sala_id, nome_arquivo):
    conn.execute("UPDATE salas SET foto = ? WHERE id = ?", (nome_arquivo, sala_id))
    conn.commit()


def importar_salas_csv(conn, conteudo_texto):
    """Espera linhas 'nome;descricao;cor'. Cria salas que ainda não
    existem (não duplica por nome). Retorna (criadas, ignoradas)."""
    leitor = csv.reader(io.StringIO(conteudo_texto), delimiter=";")
    criadas, ignoradas = 0, 0
    for linha in leitor:
        if not linha or not linha[0].strip():
            continue
        nome = linha[0].strip()
        cor = linha[2].strip() if len(linha) > 2 and linha[2].strip() else "#2563eb"
        if buscar_sala_por_nome(conn, nome):
            ignoradas += 1
            continue
        criar_sala(conn, nome, cor)
        criadas += 1
    return criadas, ignoradas


# ---------------------------------------------------------------------------
# Alunos
# ---------------------------------------------------------------------------

def listar_alunos(conn, sala_id=None, busca=None, apenas_ativos=None, turno=None):
    sql = """SELECT alunos.*, salas.nome AS sala_nome, salas.cor AS sala_cor
              FROM alunos LEFT JOIN salas ON salas.id = alunos.sala_id
              WHERE 1 = 1"""
    params = []
    if sala_id:
        sql += " AND alunos.sala_id = ?"
        params.append(sala_id)
    if busca:
        sql += " AND (alunos.nome LIKE ? OR alunos.codigo LIKE ?)"
        params.extend([f"%{busca}%", f"%{busca}%"])
    if apenas_ativos is not None:
        sql += " AND alunos.ativo = ?"
        params.append(1 if apenas_ativos else 0)
    if turno:
        sql += " AND alunos.turno = ?"
        params.append(turno)
    sql += " ORDER BY alunos.nome COLLATE NOCASE"
    return conn.execute(sql, params).fetchall()


def buscar_aluno(conn, aluno_id):
    return conn.execute(
        """SELECT alunos.*, salas.nome AS sala_nome, salas.cor AS sala_cor
           FROM alunos LEFT JOIN salas ON salas.id = alunos.sala_id
           WHERE alunos.id = ?""",
        (aluno_id,),
    ).fetchone()


def buscar_aluno_por_codigo(conn, codigo):
    return conn.execute(
        "SELECT * FROM alunos WHERE codigo = ?", (codigo,)
    ).fetchone()


TURNOS_VALIDOS = ("matutino", "vespertino", "integral")


def normalizar_turno(valor):
    """Garante que só um dos 3 valores válidos chegue no banco — usado
    tanto pelos formulários quanto pela importação de CSV. Cai para
    'matutino' se vier vazio/inválido."""
    valor = (valor or "").strip().lower()
    return valor if valor in TURNOS_VALIDOS else "matutino"


def criar_aluno(conn, nome, turma, sala_id, codigo=None, prioridade=0, turno="matutino"):
    cur = conn.execute(
        """INSERT INTO alunos (nome, turma, sala_id, codigo, prioridade, turno, status, ativo)
           VALUES (?, ?, ?, ?, ?, ?, 'aguardando', 1)""",
        (nome, turma, sala_id, codigo or None, 1 if prioridade else 0, normalizar_turno(turno)),
    )
    conn.commit()
    return cur.lastrowid


def atualizar_aluno(conn, aluno_id, nome, turma, sala_id, codigo, prioridade, turno="matutino"):
    conn.execute(
        """UPDATE alunos SET nome = ?, turma = ?, sala_id = ?, codigo = ?,
           prioridade = ?, turno = ? WHERE id = ?""",
        (nome, turma, sala_id, codigo or None, 1 if prioridade else 0, normalizar_turno(turno), aluno_id),
    )
    conn.commit()


def alternar_ativo_aluno(conn, aluno_id):
    conn.execute("UPDATE alunos SET ativo = 1 - ativo WHERE id = ?", (aluno_id,))
    conn.commit()


def excluir_aluno(conn, aluno_id):
    conn.execute("DELETE FROM alunos WHERE id = ?", (aluno_id,))
    conn.commit()


def definir_foto_aluno(conn, aluno_id, nome_arquivo):
    conn.execute("UPDATE alunos SET foto = ? WHERE id = ?", (nome_arquivo, aluno_id))
    conn.commit()


def resetar_status_aluno(conn, aluno_id):
    """Devolve um aluno chamado por engano para a fila do PERÍODO
    ATUAL: apaga a(s) chamada(s) feita(s) a ele dentro da janela do
    período (matutino/vespertino) em que estamos agora, e volta
    'status' para 'aguardando' (campo só informativo, quem manda na
    fila é a ausência de chamada no período — ver fila_kiosk()).
    Não mexe em chamadas de períodos/dias anteriores (histórico)."""
    _, inicio_periodo, fim_periodo = _janela_periodo(conn)
    conn.execute(
        "DELETE FROM chamadas WHERE aluno_id = ? AND criado_em >= ? AND criado_em < ?",
        (aluno_id, inicio_periodo, fim_periodo),
    )
    conn.execute(
        "UPDATE alunos SET status = 'aguardando' WHERE id = ?", (aluno_id,)
    )
    conn.commit()


def importar_alunos_csv(conn, conteudo_texto):
    """Espera linhas 'nome;turma;sala;codigo;turno'. 'turno' é
    opcional (cai para 'matutino' se vazio/ausente/inválido) e aceita
    'matutino', 'vespertino' ou 'integral' (integral fica disponível
    para chamada nos dois períodos). Cria a sala automaticamente se
    ainda não existir. Não duplica aluno pelo campo 'codigo' quando
    ele é informado. Retorna (criados, ignorados)."""
    leitor = csv.reader(io.StringIO(conteudo_texto), delimiter=";")
    criados, ignorados = 0, 0
    for linha in leitor:
        if not linha or not linha[0].strip():
            continue
        nome = linha[0].strip()
        turma = linha[1].strip() if len(linha) > 1 else ""
        nome_sala = linha[2].strip() if len(linha) > 2 else ""
        codigo = linha[3].strip() if len(linha) > 3 and linha[3].strip() else None
        turno = normalizar_turno(linha[4]) if len(linha) > 4 else "matutino"

        if codigo and buscar_aluno_por_codigo(conn, codigo):
            ignorados += 1
            continue

        sala_id = None
        if nome_sala:
            sala = buscar_sala_por_nome(conn, nome_sala)
            sala_id = sala["id"] if sala else criar_sala(conn, nome_sala)

        criar_aluno(conn, nome, turma, sala_id, codigo, turno=turno)
        criados += 1
    return criados, ignorados


# ---------------------------------------------------------------------------
# Exemplos (dados de teste, ver pasta exemplos/)
# ---------------------------------------------------------------------------

def importar_exemplos_iniciais(conn, exemplos_dir):
    """Deixa o sistema pronto pra testar assim que ele sobe: se ainda
    não existe NENHUMA sala cadastrada (primeira execução, banco
    novo), importa automaticamente exemplos/salas_exemplo.csv e
    exemplos/alunos_exemplo.csv, se existirem. Não faz nada se já
    houver alguma sala (nunca sobrescreve dados reais de uma escola).
    Retorna um dict com o resumo, ou None se não importou nada."""
    if contar_salas(conn) > 0:
        return None

    caminho_salas = os.path.join(exemplos_dir, "salas_exemplo.csv")
    caminho_alunos = os.path.join(exemplos_dir, "alunos_exemplo.csv")

    resumo = {"salas_criadas": 0, "alunos_criados": 0}

    if os.path.isfile(caminho_salas):
        with open(caminho_salas, "r", encoding="utf-8") as arquivo:
            criadas, _ = importar_salas_csv(conn, arquivo.read())
            resumo["salas_criadas"] = criadas

    if os.path.isfile(caminho_alunos):
        with open(caminho_alunos, "r", encoding="utf-8") as arquivo:
            criados, _ = importar_alunos_csv(conn, arquivo.read())
            resumo["alunos_criados"] = criados

    if resumo["salas_criadas"] == 0 and resumo["alunos_criados"] == 0:
        return None
    return resumo


# ---------------------------------------------------------------------------
# Presença
# ---------------------------------------------------------------------------

def _hoje():
    return datetime.date.today().isoformat()


def marcar_presenca(conn, aluno_id, status, usuario_id=None, data=None):
    data = data or _hoje()
    usuario_id_valido = usuario_id if _id_usuario_valido(conn, usuario_id) else None
    conn.execute(
        """INSERT INTO presencas (aluno_id, data, status, usuario_id)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(aluno_id, data) DO UPDATE SET
               status = excluded.status,
               usuario_id = excluded.usuario_id""",
        (aluno_id, data, status, usuario_id_valido),
    )
    conn.commit()


def esta_faltante_hoje(conn, aluno_id, data=None):
    data = data or _hoje()
    row = conn.execute(
        "SELECT status FROM presencas WHERE aluno_id = ? AND data = ?",
        (aluno_id, data),
    ).fetchone()
    return bool(row) and row["status"] == "faltante"


def presenca_do_dia(conn, data=None):
    """Retorna {aluno_id: status} só para quem tem registro no dia.
    Quem não aparece aqui é considerado presente por padrão."""
    data = data or _hoje()
    linhas = conn.execute(
        "SELECT aluno_id, status FROM presencas WHERE data = ?", (data,)
    ).fetchall()
    return {linha["aluno_id"]: linha["status"] for linha in linhas}


def listar_alunos_com_presenca_hoje(conn, sala_id=None):
    """Lista alunos ativos (opcionalmente de uma sala) já anotando o
    status de presença de hoje (presente por padrão)."""
    alunos = listar_alunos(conn, sala_id=sala_id, apenas_ativos=True)
    mapa_presenca = presenca_do_dia(conn)
    resultado = []
    for aluno in alunos:
        aluno_dict = dict(aluno)
        aluno_dict["presenca_hoje"] = mapa_presenca.get(aluno["id"], "presente")
        resultado.append(aluno_dict)
    return resultado


# ---------------------------------------------------------------------------
# Períodos (matutino / vespertino)
# ---------------------------------------------------------------------------
#
# O sistema não usa mais o campo 'alunos.status' como fonte de verdade
# para "quem pode ser chamado" — em vez disso, um aluno é considerado
# disponível sempre que ele NÃO tiver nenhuma chamada registrada
# dentro da janela de tempo do período atual (matutino ou vespertino).
# Isso faz a fila se "resetar" sozinha a cada período/dia, sem precisar
# de nenhum job agendado: assim que vira o período (ou o dia seguinte
# começa), todo mundo volta a aparecer na fila automaticamente — é
# assim que "todos os alunos ficam disponíveis para chamada no
# matutino e no vespertino" ao longo do ano letivo.
#
# O corte entre os períodos é configurável (configuracoes.hora_corte_
# periodo, formato "HH:MM", padrão "13:00") e comparado com o horário
# LOCAL do servidor — por isso as colunas criado_em usam
# datetime('now', 'localtime') no schema (ver models.py) e o Docker
# roda com TZ configurado (ver Dockerfile/docker-compose.yml). Sem
# isso, o corte compararia com UTC e desalinharia do horário real da
# escola.

def _janela_periodo(conn, quando=None):
    """Retorna (periodo, inicio, fim) — 'periodo' é 'matutino' ou
    'vespertino', e 'inicio'/'fim' são strings 'YYYY-MM-DD HH:MM:SS'
    delimitando essa janela no dia de 'quando' (ou agora, se omitido).
    Ex.: com corte 13:00, matutino = 00:00 até 13:00; vespertino =
    13:00 até 00:00 do dia seguinte."""
    quando = quando or datetime.datetime.now()
    hora_corte_texto = obter_config(conn, "hora_corte_periodo", "13:00") or "13:00"
    try:
        hora, minuto = (int(parte) for parte in hora_corte_texto.split(":", 1))
    except (ValueError, AttributeError):
        hora, minuto = 13, 0

    corte = quando.replace(hour=hora, minute=minuto, second=0, microsecond=0)
    inicio_dia = quando.replace(hour=0, minute=0, second=0, microsecond=0)
    fim_dia = inicio_dia + datetime.timedelta(days=1)

    if quando < corte:
        periodo, inicio, fim = "matutino", inicio_dia, corte
    else:
        periodo, inicio, fim = "vespertino", corte, fim_dia

    formato = "%Y-%m-%d %H:%M:%S"
    return periodo, inicio.strftime(formato), fim.strftime(formato)


def periodo_atual(conn):
    """'matutino' ou 'vespertino', com base no horário local de agora
    e no corte configurado."""
    periodo, _, _ = _janela_periodo(conn)
    return periodo


def alunos_chamados_no_periodo_atual(conn):
    """Conjunto de aluno_id que já têm alguma chamada registrada
    dentro da janela do período atual — usado pelas telas de gestão
    para mostrar "Chamado" de forma condizente com a fila real do
    Kiosk (em vez do campo 'status', que não reflete sozinho a virada
    de período)."""
    _, inicio_periodo, fim_periodo = _janela_periodo(conn)
    linhas = conn.execute(
        """SELECT DISTINCT aluno_id FROM chamadas
           WHERE aluno_id IS NOT NULL AND criado_em >= ? AND criado_em < ?""",
        (inicio_periodo, fim_periodo),
    ).fetchall()
    return {linha["aluno_id"] for linha in linhas}


# ---------------------------------------------------------------------------
# Fila de chamada / chamadas (Kiosk + Screen)
# ---------------------------------------------------------------------------

def fila_kiosk(conn, turno=None, busca=None):
    """Alunos que podem ser chamados agora: ativos, sem falta
    registrada hoje, e sem nenhuma chamada dentro do período atual
    (ver _janela_periodo — é isso que faz a fila renovar sozinha a
    cada matutino/vespertino). Quando 'turno' é informado, só entram
    alunos desse turno ou com turno 'integral' (disponíveis nos dois
    períodos). Prioridade primeiro, depois ordem alfabética."""
    _, inicio_periodo, fim_periodo = _janela_periodo(conn)
    sql = """SELECT alunos.*, salas.nome AS sala_nome, salas.cor AS sala_cor
              FROM alunos
              LEFT JOIN salas ON salas.id = alunos.sala_id
              LEFT JOIN presencas
                ON presencas.aluno_id = alunos.id AND presencas.data = ?
              WHERE alunos.ativo = 1
                AND (presencas.status IS NULL OR presencas.status != 'faltante')
                AND NOT EXISTS (
                    SELECT 1 FROM chamadas
                    WHERE chamadas.aluno_id = alunos.id
                      AND chamadas.criado_em >= ?
                      AND chamadas.criado_em < ?
                )"""
    params = [_hoje(), inicio_periodo, fim_periodo]
    if turno:
        sql += " AND (alunos.turno = ? OR alunos.turno = 'integral')"
        params.append(turno)
    if busca:
        sql += " AND alunos.nome LIKE ?"
        params.append(f"%{busca}%")
    sql += " ORDER BY alunos.prioridade DESC, alunos.nome COLLATE NOCASE"
    return conn.execute(sql, params).fetchall()


def ultimos_chamados(conn, limite=3):
    return conn.execute(
        "SELECT * FROM chamadas ORDER BY criado_em DESC, id DESC LIMIT ?",
        (limite,),
    ).fetchall()


def obter_chamada(conn, chamada_id):
    return conn.execute(
        "SELECT * FROM chamadas WHERE id = ?", (chamada_id,)
    ).fetchone()


def chamar_aluno(conn, aluno_id, usuario_id=None):
    """Chama um aluno pela primeira vez: muda status para 'chamado' e
    grava um snapshot em 'chamadas'. Retorna o snapshot (dict) pronto
    para virar o payload do evento aluno_chamado, ou None se o aluno
    não existir/não puder ser chamado."""
    aluno = buscar_aluno(conn, aluno_id)
    if not aluno or not aluno["ativo"]:
        return None

    usuario_id_valido = usuario_id if _id_usuario_valido(conn, usuario_id) else None

    conn.execute(
        "UPDATE alunos SET status = 'chamado' WHERE id = ?", (aluno_id,)
    )
    cur = conn.execute(
        """INSERT INTO chamadas (aluno_id, aluno_nome, turma, sala_nome, foto, tipo, usuario_id)
           VALUES (?, ?, ?, ?, ?, 'chamada', ?)""",
        (
            aluno["id"],
            aluno["nome"],
            aluno["turma"],
            aluno["sala_nome"],
            aluno["foto"],
            usuario_id_valido,
        ),
    )
    conn.commit()
    return dict(obter_chamada(conn, cur.lastrowid))


def rechamar_aluno(conn, aluno_id, usuario_id=None):
    """Repete a chamada de um aluno que já foi chamado, sem mudar seu
    status (ele já está 'chamado'; só repete a exibição/narração)."""
    aluno = buscar_aluno(conn, aluno_id)
    if not aluno:
        return None

    usuario_id_valido = usuario_id if _id_usuario_valido(conn, usuario_id) else None

    cur = conn.execute(
        """INSERT INTO chamadas (aluno_id, aluno_nome, turma, sala_nome, foto, tipo, usuario_id)
           VALUES (?, ?, ?, ?, ?, 'rechamada', ?)""",
        (
            aluno["id"],
            aluno["nome"],
            aluno["turma"],
            aluno["sala_nome"],
            aluno["foto"],
            usuario_id_valido,
        ),
    )
    conn.commit()
    return dict(obter_chamada(conn, cur.lastrowid))


def historico_chamadas(conn, limite=100):
    return conn.execute(
        "SELECT * FROM chamadas ORDER BY criado_em DESC, id DESC LIMIT ?",
        (limite,),
    ).fetchall()


# ---------------------------------------------------------------------------
# Configurações (chave/valor)
# ---------------------------------------------------------------------------

def obter_config(conn, chave, padrao=None):
    row = conn.execute(
        "SELECT valor FROM configuracoes WHERE chave = ?", (chave,)
    ).fetchone()
    return row["valor"] if row else padrao


def definir_config(conn, chave, valor):
    conn.execute(
        """INSERT INTO configuracoes (chave, valor) VALUES (?, ?)
           ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor""",
        (chave, valor),
    )
    conn.commit()


def obter_todas_configs(conn):
    linhas = conn.execute("SELECT chave, valor FROM configuracoes").fetchall()
    return {linha["chave"]: linha["valor"] for linha in linhas}


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

def estatisticas_dashboard(conn):
    total_alunos = conn.execute(
        "SELECT COUNT(*) AS n FROM alunos WHERE ativo = 1"
    ).fetchone()["n"]

    # "Aguardando" aqui usa a mesma regra da fila real do Kiosk
    # (ninguém chamado dentro do período atual), não o campo 'status'
    # bruto — senão o número ficaria desatualizado assim que o
    # período vira sozinho.
    _, inicio_periodo, fim_periodo = _janela_periodo(conn)
    aguardando = conn.execute(
        """SELECT COUNT(*) AS n FROM alunos
           WHERE ativo = 1
             AND NOT EXISTS (
                 SELECT 1 FROM chamadas
                 WHERE chamadas.aluno_id = alunos.id
                   AND chamadas.criado_em >= ? AND chamadas.criado_em < ?
             )""",
        (inicio_periodo, fim_periodo),
    ).fetchone()["n"]

    chamados_hoje = conn.execute(
        "SELECT COUNT(*) AS n FROM chamadas WHERE date(criado_em) = date('now', 'localtime')"
    ).fetchone()["n"]
    total_salas = conn.execute(
        "SELECT COUNT(*) AS n FROM salas WHERE ativa = 1"
    ).fetchone()["n"]
    return {
        "total_alunos": total_alunos,
        "aguardando": aguardando,
        "chamados_hoje": chamados_hoje,
        "total_salas": total_salas,
        "periodo_atual": periodo_atual(conn),
    }


# ---------------------------------------------------------------------------
# Fotos (upload + compressão automática)
# ---------------------------------------------------------------------------

def extensao_permitida(nome_arquivo, extensoes_permitidas):
    return (
        "." in nome_arquivo
        and nome_arquivo.rsplit(".", 1)[1].lower() in extensoes_permitidas
    )


def salvar_foto(arquivo_upload, pasta_destino, largura_maxima=800, qualidade=80):
    """Salva a foto enviada, comprimindo/redimensionando com Pillow
    quando disponível (evita fotos gigantes ocupando espaço/lentas
    para carregar na TV). Retorna o nome do arquivo salvo (só o nome,
    não o caminho completo — é assim que fica gravado no banco)."""
    os.makedirs(pasta_destino, exist_ok=True)
    nome_final = f"{uuid.uuid4().hex}.jpg"
    caminho_final = os.path.join(pasta_destino, nome_final)

    if Image is not None:
        imagem = Image.open(arquivo_upload.stream)
        imagem = imagem.convert("RGB")
        if imagem.width > largura_maxima:
            nova_altura = int(imagem.height * (largura_maxima / imagem.width))
            imagem = imagem.resize((largura_maxima, nova_altura))
        imagem.save(caminho_final, "JPEG", quality=qualidade, optimize=True)
    else:
        arquivo_upload.save(caminho_final)

    return nome_final


def remover_foto(pasta_destino, nome_arquivo):
    if not nome_arquivo:
        return
    caminho = os.path.join(pasta_destino, nome_arquivo)
    if os.path.exists(caminho):
        os.remove(caminho)
