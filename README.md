# Sistema de Controle de Uso da Sala de Informática da Biblioteca da UFAC

Repositório de documentação, diagramas, protótipo navegável e implementação Django do sistema web de controle de uso da Sala de Informática da Biblioteca da UFAC.

## Estado atual

O sistema já implementa reservas, sessões de uso, troca de computador, saída, ocorrências, calendário operacional, indisponibilidade de computador e relatório mensal. Usuário da Sala, Monitor da Sala e Supervisor da Biblioteca possuem interfaces funcionais e responsivas; o Administrador continua selecionável no MVP, mas sua interface própria ainda não está disponível. Consulte [docs/architecture/08-estado-implementacao.md](docs/architecture/08-estado-implementacao.md) para o detalhamento.

## Regras centrais

- consulta somente para hoje e amanhã;
- uso imediato apenas hoje;
- reservas para horários futuros de hoje ou para amanhã;
- fila de espera fora do escopo;
- ator operacional denominado Monitor da Sala;
- autorização real fora do MVP;
- computadores persistem apenas `AVAILABLE`, `MAINTENANCE` e `INACTIVE`;
- `OCCUPIED` e `RESERVED` são calculados;
- troca de computador preserva a sessão e cria nova alocação;
- relatórios são projeções dos registros operacionais.

## Executar a aplicação localmente

O caminho recomendado roda Django e Node.js no computador de desenvolvimento e
usa Docker apenas para o PostgreSQL. É o fluxo mais prático para alterar código
e ver o resultado imediatamente.

### Pré-requisitos

- Python 3.14;
- Node.js 22 com npm;
- Docker com Docker Compose.

### Primeira execução

Execute os comandos abaixo na raiz do repositório, na ordem indicada:

```bash
# 1. Cria a configuração local a partir do exemplo versionado.
cp .env.example .env

# 2. Isola as dependências Python do projeto.
python -m venv .venv
source .venv/bin/activate

# 3. Instala dependências Python e JavaScript e gera CSS/arquivos do frontend.
make install

# 4. Inicia somente o banco de desenvolvimento em segundo plano.
docker compose up -d db

# 5. Cria ou atualiza as tabelas do banco.
make migrate

# 6. Cria a base fictícia mínima para explorar a aplicação.
make seed

# 7. Inicia o servidor Django.
make run
```

Depois, abra:

- aplicação: <http://localhost:8000/>;
- documentação interativa da API: <http://localhost:8000/api/docs/>;
- documentação alternativa da API: <http://localhost:8000/api/redoc/>.

Mantenha o terminal de `make run` aberto. Para pará-lo, use `Ctrl+C`.

### O que os comandos de dados fazem

- `make migrate`: aplica as migrations pendentes. Execute após atualizar o
  repositório quando houver mudanças de modelo.
- `make seed`: cria dados canônicos de demonstração que ainda não existam. É
  incremental: não reabre calendários ou turnos encerrados e não sobrescreve
  textos, notas ou estados operacionais já editados.
- `make seed-reports`: cria uma massa histórica para demonstrar relatórios. Ele
  executa um reset explícito dos próprios dados de relatório; use-o somente em
  banco descartável de desenvolvimento.

### Configuração local e porta do banco

O Docker Compose e os comandos `make` leem o mesmo `.env` na raiz. Se a porta
`5432` já estiver ocupada, defina, por exemplo, `POSTGRES_PORT=5433` no `.env`
antes de iniciar o banco. O Django usa essa porta no computador; dentro da rede
Docker, o PostgreSQL continua na porta `5432`.

Se o terminal informar que `python` não existe, o ambiente virtual não está
ativo: execute novamente `source .venv/bin/activate`. Se a aplicação não
conseguir conectar ao banco, confirme `docker compose ps` e aguarde o serviço
`db` ficar saudável antes de repetir `make migrate`.

### Execução integral com Docker

Para executar também o Django no container, em vez de usar `make run`:

```bash
docker compose up --build -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py seed_demo_data
```

Os mesmos endereços locais continuam válidos. Veja logs com
`docker compose logs -f web` e pare os serviços com `docker compose down`.

### Reconciliação de prazos em demonstrações longas

O sistema encerra automaticamente sessões que ultrapassam o prazo operacional
e cancela reservas cujo check-in venceu. Em um ambiente em execução, agende
este comando a cada minuto:

```bash
cd backend && python manage.py reconcile_operational_deadlines
```

Ele é seguro para repetição. A documentação operacional detalhada está em
[docs/development/backend-setup.md](docs/development/backend-setup.md).

- [Guia rápido](docs/guia-rapido.md)
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

A lista completa de endpoints está em [docs/architecture/04-api.md](docs/architecture/04-api.md).

## Estrutura

- `backend/`: aplicação Django;
- `backend/apps/web/`: apresentação HTML e partials HTMX;
- `backend/static/`: fontes e assets compilados do frontend;
- `docs/product/`: regras funcionais;
- `docs/architecture/`: arquitetura corrente e API;
- `docs/adr/`: decisões arquiteturais;
- `docs/diagrams/`: UML em PlantUML;
- `prototipos/`: referência visual em HTML, CSS e JavaScript;
- `package.json`: build local de Tailwind CSS, HTMX, Alpine.js e E2E;
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
