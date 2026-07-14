# Sistema de Controle de Uso da Sala de Informática da Biblioteca da UFAC

Sistema web para substituir o registro manual de uso da Sala de Informática da Biblioteca da UFAC, controlar computadores, reservas, sessões, trocas, ocorrências e gerar relatórios derivados dos registros operacionais.

## Estado atual

A etapa 2 do backend foi iniciada. O repositório contém:

- documentação funcional, arquitetura e ADRs;
- diagramas PlantUML;
- protótipo navegável em HTML, CSS e JavaScript;
- projeto Django 5.2 LTS e Django REST Framework;
- apps modulares e modelo de domínio inicial;
- migrations iniciais para PostgreSQL;
- API `/api/v1/`, health check e OpenAPI;
- seleção de perfil de demonstração armazenada em sessão;
- testes iniciais, Ruff e GitHub Actions.

Ainda não estão implementados os serviços completos de disponibilidade, reservas, sessões, trocas, ocorrências e relatórios.

## Regras centrais

- consulta somente para hoje e amanhã;
- uso imediato apenas hoje, em horário ainda não passado;
- reserva antecipada para horário futuro de hoje ou para amanhã;
- fila de espera fora do escopo;
- ator operacional: Estagiário;
- autenticação real fora do MVP;
- computador persiste somente `AVAILABLE`, `MAINTENANCE` ou `INACTIVE`;
- `OCCUPIED` e `RESERVED` são calculados;
- troca de computador preserva a sessão e cria nova alocação;
- relatórios são projeções dos registros operacionais.

## Execução com Docker

```bash
cp .env.example .env
docker compose up --build
```

Acesse:

- aplicação: `http://localhost:8000/`;
- Swagger UI: `http://localhost:8000/api/docs/`;
- ReDoc: `http://localhost:8000/api/redoc/`;
- health check: `http://localhost:8000/api/v1/health/`.

## Execução local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements/dev.txt
docker compose up -d db
python backend/manage.py migrate
python backend/manage.py runserver
```

## Qualidade

```bash
make check
make lint
make format-check
make test
```

## Estrutura

```text
AGENTS.md
backend/                 # implementação Django
requirements/            # dependências
compose.yaml              # PostgreSQL e aplicação
prototipos/               # referência visual legada
docs/
├── product/              # regras funcionais
├── architecture/         # arquitetura vigente
├── development/          # execução e agentes
├── adr/                  # decisões arquiteturais
└── diagrams/             # UML em PlantUML
```

Consulte [docs/README.md](docs/README.md) antes de implementar novas funcionalidades.
