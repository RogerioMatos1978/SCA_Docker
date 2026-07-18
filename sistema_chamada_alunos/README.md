# Sistema de Chamada de Alunos

Aplicação web para gerenciar filas de atendimento e chamar alunos por
nome (com foto e voz) em instituições de ensino. Um operador chama um
aluno pelo terminal **Kiosk** e a chamada aparece — com foto e
narração por voz — em um painel de TV (**Screen**), em tempo real via
WebSocket, sem recarregar a página.

Esta versão implementa o **núcleo funcional** do sistema (módulos
1–7 do `PROMPT.md` original): banco de dados, login com perfis,
administração de salas e alunos (com foto e importação CSV), o Kiosk
com chamada em tempo real, a tela de TV com narração por voz e o
painel de presença diária. Os módulos avançados (histórico/exportações
em PDF/Excel, API REST, backup automático, QR Code, múltiplas
unidades/anos letivos, modo simplificado do Kiosk, roteamento
avançado por sala, etc.) ainda não estão implementados — veja
"Próximos passos" no final.

## 1. Como rodar com Docker Desktop

**Pré-requisito:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado e aberto.

1. Abra um terminal (PowerShell, no Windows) nesta pasta (`sistema_chamada_alunos`).
2. Rode:
   ```
   docker compose up --build
   ```
3. Aguarde a mensagem indicando que o servidor subiu. Abra no navegador:
   ```
   http://localhost:5000
   ```
4. Para acessar de outros dispositivos na mesma rede (TVs, tablets),
   descubra o IP do computador que está rodando o Docker (`ipconfig`
   no Windows, procure "Endereço IPv4") e acesse, por exemplo:
   ```
   http://192.168.0.10:5000
   ```

Para parar: `Ctrl+C` no terminal, depois `docker compose down`
(os dados continuam salvos nas pastas locais, veja abaixo).

Para rodar em segundo plano: `docker compose up --build -d`.
Para ver os logs depois: `docker compose logs -f`.

### Login inicial

Na primeira vez que o sistema roda, ele cria automaticamente um
usuário administrador:

- **E-mail:** `admin@local`
- **Senha:** `admin123`

Veja essa mensagem também nos logs (`docker compose logs`).
**Troque a senha assim que possível** — crie seu próprio usuário
administrador em "Usuários" e desative/atualize o padrão.

### Onde ficam os dados

O `docker-compose.yml` monta estas pastas do seu computador dentro do
container, então os dados sobrevivem a atualizações/reinícios:

- `./database/alunos.db` — banco de dados SQLite
- `./static/fotos/` — fotos de alunos
- `./static/fotos_salas/` — fotos de salas
- `./backups/`, `./logs/` — reservado para os módulos futuros de backup/log

## 2. Como usar

1. Faça login (`/login`) com o admin padrão.
2. Cadastre uma ou mais **salas** em "Salas".
3. Cadastre **alunos** em "Alunos" (manualmente ou importando um CSV — veja o botão "Importar CSV").
4. Abra o **Kiosk** (`/kiosk/`) num terminal/computador da recepção — é público, não precisa de login.
5. Abra a **TV** (`/screen/`) num navegador na TV da sala — também é pública. Na primeira vez, escolha a sala; da próxima vez ela abre direto nessa sala.
6. No Kiosk, clique em "Chamar" no nome de um aluno: ele aparece, com foto e narração por voz, na TV da sala correspondente (e nas demais telas Kiosk conectadas, na lista de "Chamados recentemente").
7. Em "Presença", marque quem faltou hoje — quem falta some da fila do Kiosk automaticamente (quem não é marcado é presente por padrão).

## 3. Formato do CSV de importação de alunos

Um aluno por linha, campos separados por `;`:

```
nome;turma;sala;codigo
Maria Silva;5º Ano A;Robótica;2026001
João Souza;5º Ano A;Robótica;2026002
```

Se a sala informada ainda não existir, ela é criada automaticamente.
Alunos com `codigo` já cadastrado são ignorados (evita duplicar ao
reimportar a mesma planilha).

## 4. Estrutura de pastas

```
sistema_chamada_alunos/
├── app.py                # application factory, rota "/", healthcheck
├── config.py              # Config / Development / Production
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── database/
│   ├── models.py           # schema SQL
│   ├── services.py          # toda a lógica de negócio e SQL
│   └── socket_events.py      # handlers Socket.IO
├── routes/                # um blueprint por área
│   ├── auth.py
│   ├── admin.py
│   ├── kiosk.py
│   ├── screen.py
│   └── presenca.py
├── templates/              # Jinja2
├── static/
│   ├── css/style.css        # CSS único do projeto
│   ├── js/                   # kiosk.js, screen.js, screen_selecionar.js
│   ├── fotos/                 # fotos de alunos
│   └── fotos_salas/            # fotos de salas
├── backups/
└── logs/
```

## 5. Rotas principais

| Rota | Público? | Descrição |
|---|---|---|
| `/` | sim | Página inicial |
| `/login`, `/logout` | sim | Autenticação |
| `/kiosk/` | **sim** | Fila de chamada (terminal) |
| `/kiosk/gestao` | login | Ativar/desativar aluno, trocar foto |
| `/screen/` | **sim** | Escolha de sala da TV |
| `/screen/geral` | **sim** | TV que reage a chamadas de qualquer sala |
| `/screen/<sala_id>` | **sim** | TV dedicada a uma sala |
| `/admin/` | login | Painel |
| `/admin/salas`, `/admin/alunos` | login (edição: admin/supervisor) | Cadastros |
| `/admin/usuarios`, `/admin/configuracoes` | admin | Gestão de usuários e configurações |
| `/presenca/` | login | Presença diária |
| `/healthcheck` | sim | Usado pelo Docker |

## 6. Rodando sem Docker (opcional, para desenvolvimento)

```
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
Acesse `http://localhost:5000`.

## 7. Próximos passos (não implementados nesta versão)

- Histórico completo de chamadas e exportações (CSV/Excel/PDF)
- API REST
- Backup automático/manual e restauração, QR Code, tema claro/escuro, som de aviso
- Múltiplos guichês, "rechamar mantendo dados originais" com histórico completo
- Ano letivo, aluno ativo/inativo por transferência, múltiplas unidades/campi
- Kiosk em "modo simplificado" dedicado (já existe a configuração no banco, falta a tela reduzida)
- Auditoria (`logs_auditoria`)

O `docker-compose.yml`, `config.py` e `database/models.py` já foram
desenhados pensando nessa evolução (pastas de backup/log já existem,
schema já usa o padrão de migração segura com `ALTER TABLE`), então
dá para adicionar os módulos seguintes incrementalmente sem reescrever
a base.
