# Configuração do backend

## Pré-requisitos

- Python 3.14;
- Node.js 22 e npm;
- Docker com Docker Compose;
- PostgreSQL 17 quando executado fora do Compose.

## Execução local

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
make install
docker compose up -d db
make migrate
make seed
make run
```

A aplicação ficará em `http://localhost:8000/` e a documentação OpenAPI em `http://localhost:8000/api/docs/`.

O Compose e os comandos `make` carregam as variáveis do `.env` da raiz. Se a
porta `5432` já estiver em uso, altere `POSTGRES_PORT` nesse arquivo para uma
porta livre, como `5433`, antes de subir o banco. O PostgreSQL continua ouvindo
em `5432` dentro da rede do Compose.

O comando `make seed` é idempotente e cria oito computadores fictícios, os três turnos iniciais, uma política de reservas e a configuração padrão de relatórios.

`make install` instala as dependências Python e npm e gera os assets locais. O CSS compilado e as cópias de HTMX e Alpine.js são versionados, portanto a imagem Docker não precisa de Node.js em produção.

## Reconciliação de prazos

Em ambiente em execução, agende o comando abaixo a cada minuto. Ele cancela reservas cujo check-in venceu e registra automaticamente a saída de sessões que chegaram ao prazo máximo:

```bash
cd backend && python manage.py reconcile_operational_deadlines
```

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
- área funcional do Usuário da Sala com computadores, agenda, sessão e problemas;
- health check;
- computadores e estado operacional com histórico;
- turnos e calendário operacional (regular, temporário e exceções);
- política de reservas versionada;
- disponibilidade para hoje e amanhã com slots de 15 minutos;
- reservas com cancelamento e deadlines;
- sessões de uso: entrada, troca de computador, saída e correção;
- ocorrências;
- indisponibilidade de computador com transferência/realocação atômica;
- relatório mensal JSON.

Consulte [../architecture/08-estado-implementacao.md](../architecture/08-estado-implementacao.md) para o detalhamento do que já foi entregue.
