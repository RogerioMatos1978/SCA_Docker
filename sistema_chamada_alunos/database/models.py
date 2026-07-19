"""
Definição do schema do banco de dados (SQLite puro, sem ORM) e funções
para abrir conexão / inicializar o banco.

Padrão de migração segura usado neste projeto:
1. TABLES_SQL roda primeiro — todas as tabelas usam
   "CREATE TABLE IF NOT EXISTS", então nunca apaga dados existentes.
2. _migrar_colunas_novas() roda depois — tenta "ALTER TABLE ... ADD
   COLUMN" para cada coluna nova, ignorando erro se ela já existir.
   Isso permite adicionar campos novos sem quebrar instalações antigas.
3. INDEXES_SQL roda por último, porque alguns índices podem depender
   de colunas que só existem depois da migração.

Ao adicionar uma coluna nova a uma tabela já existente no futuro,
siga esse padrão: não coloque a coluna direto em TABLES_SQL, adicione
em _COLUNAS_NOVAS também.
"""

import sqlite3
import os

TABLES_SQL = """
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    usuario TEXT NOT NULL UNIQUE,
    senha_hash TEXT NOT NULL,
    perfil TEXT NOT NULL DEFAULT 'operador'
        CHECK (perfil IN ('administrador', 'supervisor', 'operador')),
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS salas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE,
    cor TEXT NOT NULL DEFAULT '#2563eb',
    ordem INTEGER NOT NULL DEFAULT 0,
    ativa INTEGER NOT NULL DEFAULT 1,
    foto TEXT,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS alunos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    turma TEXT,
    sala_id INTEGER REFERENCES salas(id) ON DELETE SET NULL,
    foto TEXT,
    codigo TEXT UNIQUE,
    prioridade INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'aguardando'
        CHECK (status IN ('aguardando', 'chamado')),
    -- turno em que o aluno tem aula/deve ficar disponível para
    -- chamada: 'matutino', 'vespertino' ou 'integral' (integral
    -- aparece na fila nos dois períodos). Ver services._janela_periodo.
    turno TEXT NOT NULL DEFAULT 'matutino'
        CHECK (turno IN ('matutino', 'vespertino', 'integral')),
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS presencas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    aluno_id INTEGER NOT NULL REFERENCES alunos(id) ON DELETE CASCADE,
    data TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'presente'
        CHECK (status IN ('presente', 'faltante')),
    usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    UNIQUE (aluno_id, data)
);

CREATE TABLE IF NOT EXISTS chamadas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    aluno_id INTEGER,
    aluno_nome TEXT NOT NULL,
    turma TEXT,
    sala_nome TEXT,
    foto TEXT,
    tipo TEXT NOT NULL DEFAULT 'chamada'
        CHECK (tipo IN ('chamada', 'rechamada', 'manual')),
    usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS configuracoes (
    chave TEXT PRIMARY KEY,
    valor TEXT
);
"""

# Colunas adicionadas depois da v1 do schema. Formato:
# (tabela, nome_da_coluna, definicao_sql_da_coluna)
_COLUNAS_NOVAS = [
    # v1 do sistema fazia login por e-mail (coluna "email"). A coluna
    # "usuario" já vem em TABLES_SQL para instalações novas; esta
    # entrada garante que um banco de uma instalação antiga (criado
    # antes dessa mudança) também ganhe a coluna "usuario" sem perder
    # dados — o backfill (copiar email -> usuario) roda logo depois,
    # em _migrar_login_email_para_usuario().
    ("usuarios", "usuario", "TEXT"),
    # Turno do aluno (matutino/vespertino/integral), usado para saber
    # em qual período ele deve aparecer na fila do Kiosk. Sem CHECK
    # aqui de propósito — ALTER TABLE ADD COLUMN do SQLite tem
    # restrições; a validação do valor já é garantida pela aplicação
    # (formulário usa <select> com essas 3 opções, e a importação de
    # CSV cai para 'matutino' se vier um valor inválido/vazio).
    ("alunos", "turno", "TEXT NOT NULL DEFAULT 'matutino'"),
    # Exemplo de como adicionar uma coluna nova no futuro sem quebrar
    # bancos já existentes:
    # ("alunos", "observacoes", "TEXT"),
]

INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS idx_alunos_sala ON alunos(sala_id);
CREATE INDEX IF NOT EXISTS idx_alunos_status ON alunos(status);
CREATE INDEX IF NOT EXISTS idx_alunos_ativo ON alunos(ativo);
CREATE INDEX IF NOT EXISTS idx_presencas_aluno_data ON presencas(aluno_id, data);
CREATE INDEX IF NOT EXISTS idx_chamadas_criado_em ON chamadas(criado_em);
"""

_CONFIGURACOES_PADRAO = {
    "nome_instituicao": "Minha Instituição de Ensino",
    "destino_chamada": "Portaria de Saída",
    "kiosk_modo_simplificado": "0",
    # Horário (HH:MM, hora local do servidor) que separa o período
    # matutino do vespertino. Usado pelo Kiosk para: 1) escolher
    # automaticamente qual período mostrar, e 2) decidir se um aluno
    # já chamado "neste período" deve sumir da fila (ele volta sozinho
    # assim que o período muda, sem precisar de reset manual). Ver
    # services._janela_periodo().
    "hora_corte_periodo": "13:00",
}


def get_db(database_path):
    """Abre uma conexão com o SQLite, com linhas acessíveis por nome
    de coluna (sqlite3.Row) e chaves estrangeiras habilitadas."""
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _migrar_colunas_novas(conn):
    for tabela, coluna, definicao in _COLUNAS_NOVAS:
        try:
            conn.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {definicao}")
        except sqlite3.OperationalError:
            # Coluna já existe — ignora e segue.
            pass


def _migrar_login_email_para_usuario(conn):
    """Instalações antigas faziam login por e-mail (coluna 'email').
    Se essa coluna ainda existir (banco antigo), copia o valor para a
    coluna 'usuario' nos registros que ainda não têm 'usuario'
    preenchido — assim ninguém perde o acesso na troca de e-mail para
    usuário como identificador de login."""
    colunas = [linha["name"] for linha in conn.execute("PRAGMA table_info(usuarios)").fetchall()]
    if "email" not in colunas:
        return  # instalação nova: essa coluna nunca existiu
    conn.execute(
        "UPDATE usuarios SET usuario = email WHERE usuario IS NULL AND email IS NOT NULL"
    )


def _garantir_indice_unico_usuario(conn):
    """Cria o índice único de 'usuario' à parte (não dentro do script
    de INDEXES_SQL) para não travar a inicialização inteira caso uma
    instalação antiga migrada tenha, por algum motivo raro, valores
    duplicados — nesse caso só logamos e seguimos, em vez de impedir o
    sistema de subir."""
    try:
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_usuarios_usuario ON usuarios(usuario)"
        )
    except sqlite3.IntegrityError:
        pass


def _garantir_configuracoes_padrao(conn):
    for chave, valor in _CONFIGURACOES_PADRAO.items():
        conn.execute(
            "INSERT OR IGNORE INTO configuracoes (chave, valor) VALUES (?, ?)",
            (chave, valor),
        )


def init_db(database_path):
    """Cria as tabelas/índices se não existirem e roda migrações
    simples. Nunca apaga dados existentes."""
    os.makedirs(os.path.dirname(database_path), exist_ok=True)
    conn = get_db(database_path)
    try:
        conn.executescript(TABLES_SQL)
        _migrar_colunas_novas(conn)
        _migrar_login_email_para_usuario(conn)
        conn.executescript(INDEXES_SQL)
        _garantir_indice_unico_usuario(conn)
        _garantir_configuracoes_padrao(conn)
        conn.commit()
    finally:
        conn.close()
