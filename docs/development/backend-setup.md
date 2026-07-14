# Configuração do backend

## Pré-requisitos

- Python 3.12;
- Docker com Docker Compose;
- PostgreSQL 17 quando executado fora do Compose.

## Execução local

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -r requirements/dev.txt
docker compose up -d db
make migrate
make seed
make run
```

A aplicação ficará em `http://localhost:8000/` e a documentação OpenAPI em `http://localhost:8000/api/docs/`.

O comando `make seed` é idempotente e cria oito computadores fictícios, os três turnos iniciais, uma política de reservas e a configuração padrão de relatórios.

## Execução integral com Docker

```bash
docker compose up --build
```

Em outro terminal, execute as migrations e o seed no container da aplicação quando necessário.

## Comandos de qualidade

```bash
make check
make lint
make format-check
make test
```

## Funcionalidades disponíveis

- seleção de perfil de demonstração;
- health check;
- computadores e estado operacional;
- histórico das alterações de estado;
- turnos;
- exceções de calendário;
- política de duração dos slots;
- disponibilidade para hoje e amanhã;
- slots derivados de configuração, reservas e alocações.

Ainda não estão disponíveis criação e cancelamento de reservas, entrada, troca, saída, tratamento de ocorrências via API e relatórios.
