# Configuração inicial do backend

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
python backend/manage.py migrate
python backend/manage.py runserver
```

A aplicação ficará em `http://localhost:8000/` e a documentação OpenAPI em `http://localhost:8000/api/docs/`.

## Execução integral com Docker

```bash
docker compose up --build
```

## Comandos de qualidade

```bash
make check
make lint
make format-check
make test
```

## Escopo desta etapa

O scaffold inicial inclui:

- configurações separadas para ambiente local, testes e produção;
- PostgreSQL;
- apps por domínio;
- modelos e migrations iniciais;
- API `/api/v1/`;
- OpenAPI com Swagger UI e ReDoc;
- health check;
- seleção de perfil de demonstração armazenada em sessão;
- testes iniciais e CI.

Ainda não estão implementados os serviços de disponibilidade, reserva, entrada, troca, saída, ocorrências via API ou relatórios.
