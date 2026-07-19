# Sistema de Chamada de Alunos

Aplicação web para gerenciar filas de atendimento e chamar alunos por
nome (com foto e voz) em instituições de ensino. Um operador chama um
aluno pelo terminal **Kiosk** e a chamada aparece — com foto e
narração por voz — em um painel de TV (**Screen**), em tempo real via
WebSocket, sem recarregar a página. Tema visual "Matrix" (preto/verde).

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

Para rodar em segundo plano (recomendado para deixar sempre no ar):
`docker compose up --build -d`. Para ver os logs depois:
`docker compose logs -f`.

## 2. Rede local (Kiosk na portaria, TVs nas salas)

O `docker-compose.yml` já publica a porta 5000 em **todas as
interfaces de rede** do computador (`"5000:5000"`), e o Flask já sobe
com `host="0.0.0.0"` — ou seja, qualquer dispositivo na mesma rede
Wi-Fi/cabeada já consegue acessar o sistema, sem configuração extra.

Para descobrir o IP do computador que está rodando o Docker:
- **Windows:** abra o PowerShell e rode `ipconfig`, procure "Endereço IPv4" (normalmente `192.168.x.x`).
- **macOS/Linux:** rode `ifconfig` ou `ip addr`.

Nos outros dispositivos da rede (Kiosk na recepção, TVs nas salas,
celulares/tablets para gerenciar), acesse:
```
http://SEU-IP-AQUI:5000
```
Por exemplo, `http://192.168.0.10:5000/kiosk/` no terminal da portaria
e `http://192.168.0.10:5000/screen/` em cada TV.

**Firewall do Windows:** na primeira vez que o Docker Desktop expõe a
porta, o Windows pode perguntar se permite a conexão na rede — escolha
"Permitir acesso" para redes privadas. Se outros dispositivos não
conseguirem conectar, confira se a porta 5000 está liberada no
firewall para a rede local.

**IP fixo:** como o endereço IP do computador pode mudar (DHCP), vale
configurar um IP fixo/reserva de DHCP para ele no roteador, para as
TVs e o Kiosk não perderem a conexão depois de reiniciar o roteador.

## 3. Sistema sempre pronto quando o Docker inicia

Duas coisas garantem isso:

1. **`restart: unless-stopped`** no `docker-compose.yml` — o container
   reinicia sozinho toda vez que o Docker Desktop/serviço do Docker é
   reiniciado (computador reiniciou, Docker Desktop foi fechado e
   reaberto), sem precisar rodar `docker compose up` de novo na mão.
   Isso só vale enquanto o container não for removido: use
   `docker compose stop` para pausar (ele retoma sozinho depois) em
   vez de `docker compose down` (que remove o container — nesse caso
   você precisa rodar `docker compose up -d` de novo manualmente).
2. **Auto-carregamento de dados de exemplo** (ver seção 4 abaixo) — o
   sistema já sobe com salas e alunos de teste na primeira vez, sem
   precisar importar nada manualmente antes de usar.

Para o Docker Desktop já estar rodando sozinho quando o Windows liga,
ative em Docker Desktop → Settings → General → **"Start Docker Desktop
when you sign in"**.

## 4. Dados de exemplo (pasta `exemplos/`)

A pasta `exemplos/` traz dois CSVs prontos para teste:

- **`salas_exemplo.csv`** — 14 salas, uma por componente curricular da
  BNCC (Base Nacional Comum Curricular / MEC) do Ensino Fundamental —
  Anos Finais e do Ensino Médio: Língua Portuguesa, Matemática,
  Ciências, Geografia, História, Arte, Educação Física, Língua
  Inglesa, Ensino Religioso, Biologia, Física, Química, Sociologia e
  Filosofia.
- **`alunos_exemplo.csv`** — 39 alunos fictícios, distribuídos em
  turmas do 6º ao 9º ano (Fundamental) e da 1ª à 3ª série (Médio),
  cada um associado a uma das salas acima e com um **turno** definido
  (22 matutino, 12 vespertino, 5 integral) — ver seção 7 sobre
  períodos.

**Esses dois arquivos são importados automaticamente** na primeira vez
que o sistema roda (banco de salas vazio) — é assim que ele já sobe
"pronto pra usar". Se você não quiser dados fictícios (ex.: instalação
real de uma escola), desligue isso definindo no `docker-compose.yml`:
```yaml
environment:
  - AUTO_IMPORTAR_EXEMPLOS=0
```
Você também pode editar os CSVs em `exemplos/` antes do primeiro
`docker compose up` (a pasta é montada no container) para já subir com
os dados reais da sua escola, ou reimportá-los manualmente a qualquer
momento em Alunos → Importar CSV / Salas → Importar CSV.

## 5. Login inicial

Na primeira vez que o sistema roda, ele cria automaticamente um
usuário administrador:

- **Usuário:** `admin`
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
- `./exemplos/` — CSVs de exemplo (editável, montado somente leitura)
- `./backups/`, `./logs/` — reservado para os módulos futuros de backup/log

## 6. Como usar

1. Faça login (`/login`) com o admin padrão.
2. As salas e os alunos de exemplo (seção 4) já estão cadastrados —
   ou cadastre os seus próprios em "Salas" e "Alunos".
3. Abra o **Kiosk** (`/kiosk/`) num terminal/computador da recepção — é público, não precisa de login.
4. Abra a **TV** (`/screen/`) num navegador na TV da sala — também é pública. Na primeira vez, escolha a sala; da próxima vez ela abre direto nessa sala.
5. No Kiosk, clique em "Chamar" no nome de um aluno: ele aparece, com foto e narração por voz, na TV da sala correspondente (e nas demais telas Kiosk conectadas, na lista de "Chamados recentemente").
6. Em "Presença", marque quem faltou hoje — quem falta some da fila do Kiosk automaticamente (quem não é marcado é presente por padrão).

## 7. Períodos: Matutino e Vespertino

Todo aluno tem um **turno** (`matutino`, `vespertino` ou `integral`) e
fica disponível para chamada no(s) período(s) correspondente(s) — um
aluno `integral` aparece na fila nos dois períodos.

A fila do Kiosk **se renova sozinha** a cada virada de período e a
cada novo dia: um aluno chamado de manhã reaparece automaticamente na
fila assim que vira o período da tarde (e todo mundo reaparece de novo
no dia seguinte), sem precisar de nenhum reset manual ou tarefa
agendada. Isso funciona porque o sistema não usa mais um simples
"já foi chamado sim/não" — ele verifica se existe alguma chamada
registrada **dentro da janela de tempo do período atual**.

- O horário que separa Matutino de Vespertino é configurável em
  **Configurações → Horário de corte** (padrão `13:00`, horário local
  do servidor).
- O Kiosk mostra abas **☀️ Matutino / 🌇 Vespertino** para forçar a
  visualização de um período específico (por exemplo, se o operador
  quiser conferir a fila da tarde antes de bater o horário) — clicando
  em "Voltar para automático" o Kiosk volta a escolher sozinho, com
  base no horário atual.
- Como a virada de período depende do **horário local do servidor**,
  o `Dockerfile`/`docker-compose.yml` já configuram o fuso horário do
  container (`TZ=America/Sao_Paulo` por padrão — troque nos dois
  arquivos se a escola ficar em outro fuso; lista de fusos válidos em
  https://en.wikipedia.org/wiki/List_of_tz_database_time_zones).
- Em "Gestão" (`/kiosk/gestao`) e em "Alunos", o botão "Voltar p/
  fila" desfaz a chamada feita ao aluno **dentro do período atual**,
  devolvendo-o pra fila imediatamente (sem esperar a próxima virada).

## 8. Formato dos CSVs de importação

**Alunos** — um aluno por linha, campos separados por `;`:
```
nome;turma;sala;codigo;turno
Maria Silva;5º Ano A;Robótica;2026001;matutino
João Souza;5º Ano A;Robótica;2026002;vespertino
```
Se a sala informada ainda não existir, ela é criada automaticamente.
Alunos com `codigo` já cadastrado são ignorados (evita duplicar ao
reimportar a mesma planilha). O campo `turno` é opcional — aceita
`matutino`, `vespertino` ou `integral`; vazio ou inválido vira
`matutino` (ver seção 7).

**Salas** — uma sala por linha, campos separados por `;`:
```
nome;descricao;cor
Matemática;Sala de Matemática;#2563eb
```

## 9. Estrutura de pastas

```
sistema_chamada_alunos/
├── app.py                # application factory, rota "/", healthcheck
├── config.py              # Config / Development / Production
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── exemplos/               # CSVs de salas/alunos de teste (BNCC/MEC)
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
│   ├── css/style.css        # CSS único do projeto (tema Matrix)
│   ├── js/                   # kiosk.js, screen.js, screen_selecionar.js, matrix-rain.js
│   ├── fotos/                 # fotos de alunos
│   └── fotos_salas/            # fotos de salas
├── backups/
└── logs/
```

## 10. Rotas principais

| Rota | Público? | Descrição |
|---|---|---|
| `/` | sim | Página inicial |
| `/login`, `/logout` | sim | Autenticação (login por usuário, não e-mail) |
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

## 11. Rodando sem Docker (opcional, para desenvolvimento)

```
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
Acesse `http://localhost:5000`.

## 12. Próximos passos (não implementados nesta versão)

- Histórico completo de chamadas e exportações (CSV/Excel/PDF)
- API REST
- Backup automático/manual e restauração, QR Code, som de aviso
- Múltiplos guichês, "rechamar mantendo dados originais" com histórico completo
- Ano letivo, aluno ativo/inativo por transferência, múltiplas unidades/campi
- Kiosk em "modo simplificado" dedicado (já existe a configuração no banco, falta a tela reduzida)
- Auditoria (`logs_auditoria`)

O `docker-compose.yml`, `config.py` e `database/models.py` já foram
desenhados pensando nessa evolução (pastas de backup/log já existem,
schema já usa o padrão de migração segura com `ALTER TABLE`), então
dá para adicionar os módulos seguintes incrementalmente sem reescrever
a base.
