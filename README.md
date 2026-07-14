# Sistema de Controle de Uso da Sala de Informática da Biblioteca da UFAC

Repositório de documentação, diagramas, protótipo navegável e implementação Django do sistema web de controle de uso da Sala de Informática da Biblioteca da UFAC.

## Estado atual

As etapas documentais e de inicialização do backend foram concluídas. O backend já possui:

- Django 5.2 e Django REST Framework;
- PostgreSQL via Docker Compose;
- apps separados por domínio;
- seleção de perfil de demonstração em sessão;
- modelos e migrations iniciais;
- CRUD inicial de computadores, turnos e exceções de calendário;
- alteração auditável do estado operacional dos computadores;
- política de duração dos slots;
- geração de slots para hoje e amanhã;
- cálculo de `AVAILABLE`, `MAINTENANCE`, `INACTIVE`, `OCCUPIED` e `RESERVED`;
- OpenAPI, testes, Ruff e CI.

## Regras centrais

- consulta somente para hoje e amanhã;
- uso imediato apenas hoje;
- reservas para horários futuros de hoje ou para amanhã;
- fila de espera fora do escopo;
- ator operacional denominado Estagiário;
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
make run
```

A aplicação fica em `http://localhost:8000/`.

Documentação da API:

```text
http://localhost:8000/api/docs/
http://localhost:8000/api/redoc/
```

## Endpoints disponíveis

```text
GET  /api/v1/health/
GET  /api/v1/demo/context/
POST /api/v1/demo/select-profile/

GET  /api/v1/computers/
POST /api/v1/computers/
GET  /api/v1/computers/{id}/
PATCH /api/v1/computers/{id}/
PATCH /api/v1/computers/{id}/operational-state/
GET  /api/v1/computers/availability/?date=YYYY-MM-DD
GET  /api/v1/computers/{id}/slots/?date=YYYY-MM-DD

GET  /api/v1/shifts/
POST /api/v1/shifts/
PATCH /api/v1/shifts/{id}/
GET  /api/v1/calendar-exceptions/
POST /api/v1/calendar-exceptions/
PATCH /api/v1/calendar-exceptions/{id}/
GET  /api/v1/booking-policy/
PATCH /api/v1/booking-policy/
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

Implementar reservas e sessões em uma fatia transacional: criação e cancelamento de reservas, entrada, sessão ativa, troca de computador e saída.
