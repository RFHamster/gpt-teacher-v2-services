# gpt-teacher-feedback-service

Microsserviço de feedback do **GPT Teacher**. Atua como um **segundo leitor** do mesmo banco PostgreSQL usado pelo `gpt-teacher-v2-backend`, reutilizando os modelos do pacote compartilhado `gpt_teacher_db` (instalado em modo editável), sem duplicar definições de tabela.

---

## Visão Geral

```
┌─────────────────────────────────────────────┐
│            gpt-teacher-v2-backend            │  ← porta 8000
│              (serviço principal)             │
└───────────────────┬─────────────────────────┘
                    │ leitura/escrita
                    ▼
          ┌─────────────────┐
          │   PostgreSQL     │  ← banco compartilhado
          └────────┬────────┘
                   │ somente leitura
                   ▼
┌──────────────────────────────────────────────┐
│       gpt-teacher-feedback-service            │  ← porta 8001
│  (este serviço — gera relatórios de feedback) │
└──────────────────────────────────────────────┘
```

O serviço expõe um endpoint HTTP que dispara, em **background**, a geração de um relatório de feedback consolidado por turma. O disparo retorna imediatamente (`202 Accepted`) enquanto o processamento acontece de forma assíncrona.

---

## Estrutura do Projeto

```
gpt-teacher-feedback-service/
├── app/
│   ├── main.py                    # entrypoint FastAPI; registra routers e o health check
│   ├── api/
│   │   └── routes/
│   │       └── feedback.py        # POST /api/v1/feedback/generate
│   ├── services/
│   │   └── feedback_service.py    # lógica de geração do relatório (BackgroundTask)
│   └── core/
│       ├── config.py              # leitura das variáveis de ambiente via Pydantic Settings
│       └── db.py                  # engine SQLModel e fábrica de sessões independentes
├── pyproject.toml                 # dependências gerenciadas com uv
├── uv.lock                        # lockfile reproduzível
├── .python-version                # versão do Python (3.12)
├── .env.example                   # modelo de variáveis de ambiente (crie um .env local)
└── README.md
```

---

## Pré-requisitos

| Ferramenta | Versão mínima |
|------------|---------------|
| Python     | 3.12          |
| uv         | qualquer      |
| PostgreSQL  | 14+           |

O pacote `gpt-teacher-db` precisa estar disponível no caminho relativo `../../../gpt-teacher-db/gpt-teacher-db` (veja `pyproject.toml → [tool.uv.sources]`).

---

## Configuração

Crie um arquivo `.env` na raiz do serviço (nunca versione este arquivo):

```dotenv
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=sua_senha
POSTGRES_DB=gpt_teacher
```

---

## Instalação e Execução

```bash
# instala dependências (cria .venv automaticamente)
uv sync

# inicia o servidor na porta 8001
uv run uvicorn app.main:app --reload --port 8001
```

A porta **8001** evita conflito com o backend principal (porta 8000).

---

## Endpoints

### `GET /health`
Retorna o status do serviço.

```json
{ "status": "ok" }
```

---

### `POST /api/v1/feedback/generate`
Dispara a geração do relatório de feedback em **segundo plano**.

- **Resposta imediata:** `202 Accepted`
- **Processamento assíncrono:** a geração do relatório abre sua própria sessão de banco de dados e não bloqueia a resposta HTTP.

**Resposta:**
```json
{ "message": "Geração de feedback iniciada em segundo plano." }
```

**O relatório gerado (logado no terminal do uvicorn):**
```
INFO  Turma 'Turma A' (uuid): 12 sessões, 87 mensagens (43 do aluno, 44 da IA)
INFO  Turma 'Turma B' (uuid): 8 sessões, 55 mensagens (28 do aluno, 27 da IA)
INFO  Relatório de feedback concluído em 2026-09-26T14:00:00+00:00
```

---

## Documentação Interativa (Swagger)

Com o servidor rodando, acesse:

```
http://127.0.0.1:8001/docs
```

---

## Como o Relatório É Gerado

O `feedback_service.generate_feedback_report()` executa os seguintes passos:

1. Busca todas as **turmas** (`Classroom`) no banco.
2. Para cada turma, busca os **problemas** (`Problem`) associados.
3. Para cada problema, busca as **sessões de aluno** (`StudentSession`).
4. Para cada sessão, conta as **mensagens** (`ChatMessage`), separando por tipo (`USER` / `AI`).
5. Loga um resumo consolidado por turma.

A função não recebe parâmetros por design — ela abre sua própria sessão e lê tudo do banco, o que permite trocar o mecanismo de disparo (hoje HTTP + `BackgroundTask`) por um consumidor de fila no futuro sem alterar a lógica de negócio.

---

## Tecnologias

| Biblioteca         | Função                                      |
|--------------------|---------------------------------------------|
| FastAPI            | Framework HTTP assíncrono                   |
| SQLModel           | ORM (camada sobre SQLAlchemy + Pydantic)    |
| psycopg (v3)       | Driver PostgreSQL nativo                    |
| Pydantic Settings  | Gerenciamento de configuração via `.env`    |
| uvicorn            | Servidor ASGI                               |
| uv                 | Gerenciador de pacotes e ambientes virtuais |

---

## Desenvolvimento

```bash
# executar em modo desenvolvimento com auto-reload
uv run uvicorn app.main:app --reload --port 8001

# verificar tipagem estática (opcional)
uv run mypy app/
```
