# Sistema de Controle de Uso da Sala de Informática da Biblioteca da UFAC

Repositório de documentação, diagramas, protótipo navegável e implementação Django do sistema web de controle de uso da Sala de Informática da Biblioteca da UFAC.

## Estado atual

As etapas documentais e de inicialização do backend foram concluídas. O backend já possui:

- Django 5.2 e Django REST Framework;
- PostgreSQL via Docker Compose;
- apps separados por domínio;
- seleção de perfil de demonstração em sessão;
- referência, vínculo e unidade fictícios para Usuário da Sala;
- modelos e migrations iniciais;
- CRUD inicial de computadores, turnos e exceções de calendário;
- substituição versionada de turnos com auditoria;
- identidade lógica compartilhada entre versões do mesmo turno;
- alteração auditável do estado operacional dos computadores;
- política de duração dos slots;
- criação e cancelamento transacionais de reservas;
- entrada, sessão ativa, troca de computador e saída transacionais;
- geração de slots para hoje e amanhã;
- cálculo de `AVAILABLE`, `MAINTENANCE`, `INACTIVE`, `OCCUPIED` e `RESERVED`;
- OpenAPI, testes, Ruff e CI;
- relatório mensal JSON derivado dos registros operacionais.

## Regras centrais

- consulta somente para hoje e amanhã;
- uso imediato apenas hoje;
- reservas para horários futuros de hoje ou para amanhã;
- fila de espera fora do escopo;
- ator operacional denominado Monitor da Sala;
- autenticação real fora do MVP;
- computadores persistem apenas `AVAILABLE`, `MAINTENANCE` e `INACTIVE`;
- `OCCUPIED` e `RESERVED` são calculados;
- troca de computador preserva a sessão e cria nova alocação;
- relatórios são projeções dos registros operacionais.

## Execução do backend

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -r requirements/dev.txt
docker compose up -d db
make migrate
make seed
make seed-reports
make run
```

A aplicação fica em `http://localhost:8000/`.

- [Índice da documentação](docs/README.md)
- [Visão geral do produto](docs/product/00-visao-geral.md)
- [Escopo do MVP](docs/product/01-escopo-mvp.md)
- [Regras de negócio](docs/product/03-regras-de-negocio.md)
- [Visão geral da arquitetura](docs/architecture/00-visao-geral.md)
- [Modelo de domínio](docs/architecture/02-modelo-de-dominio.md)
- [API](docs/architecture/04-api.md)
- [Índice de ADRs](docs/adr/README.md)
- [Índice dos diagramas](docs/diagrams/README.md)
- [Instruções para agentes](AGENTS.md)
- [Instalação e uso de skills no Cline e Codex](docs/development/agent-skills.md)

Documentação da API:

```text
http://localhost:8000/api/docs/
http://localhost:8000/api/redoc/
```

## Endpoints disponíveis

```text
GET  /api/health/
GET  /api/demo/context/
POST /api/demo/select-profile/

GET  /api/computers/
POST /api/computers/
GET  /api/computers/{id}/
PATCH /api/computers/{id}/
PATCH /api/computers/{id}/operational-state/
GET  /api/computers/availability/?date=YYYY-MM-DD
GET  /api/computers/{id}/slots/?date=YYYY-MM-DD

GET  /api/shifts/
POST /api/shifts/
PATCH /api/shifts/{id}/
POST /api/shifts/{id}/replace/
GET  /api/calendar-exceptions/
POST /api/calendar-exceptions/
PATCH /api/calendar-exceptions/{id}/
GET  /api/booking-policy/
PATCH /api/booking-policy/

GET  /api/reservations/
GET  /api/reservations/mine/
POST /api/reservations/
POST /api/reservations/{id}/cancel/

GET  /api/usage-sessions/current/
GET  /api/usage-sessions/active/
GET  /api/usage-sessions/history/
POST /api/usage-sessions/start/
POST /api/usage-sessions/{id}/switch-computer/
POST /api/usage-sessions/{id}/finish/
POST /api/usage-sessions/{id}/correct/

GET   /api/occurrences/
POST  /api/occurrences/
GET   /api/occurrences/{id}/
PATCH /api/occurrences/{id}/

GET /api/reports/monthly/?year=YYYY&month=M
```

## Estrutura

- `backend/`: aplicação Django;
- `docs/product/`: regras funcionais;
- `docs/architecture/`: arquitetura corrente e API;
- `docs/adr/`: decisões arquiteturais;
- `docs/diagrams/`: UML em PlantUML;
- `prototipos/`: referência visual em HTML, CSS e JavaScript;
- `AGENTS.md`: instruções para agentes de código.

## Qualidade

```bash
make check
make lint
make format-check
make test
```

## Próxima etapa

Implementar as demais projeções e exportações a partir das mesmas regras do relatório mensal.
