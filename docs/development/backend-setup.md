# Configuração do backend

## Pré-requisitos

- Python 3.14;
- Node.js 22 e npm;
- Docker com Docker Compose;
- PostgreSQL 17 quando executado fora do Compose.

O PostgreSQL 17 já está definido no Compose. Instale-o diretamente somente se
quiser executar o banco fora do Docker.

## Fluxo recomendado: backend no host e banco no Docker

Esse fluxo mantém o Django no terminal local, com reload automático, e isola
apenas o PostgreSQL no container. Execute tudo a partir da raiz do repositório.

### 1. Preparar a configuração e as dependências

```bash
# Crie o arquivo local. Ele não é versionado e pode conter ajustes da máquina.
cp .env.example .env

# Crie e ative o ambiente Python. A ativação faz `python` e `pip` apontarem
# para as dependências do projeto durante esta sessão de terminal.
python -m venv .venv
source .venv/bin/activate

# Instale dependências Python/Node e gere os assets versionados do frontend.
make install
```

`make install` equivale à instalação via `pip`, `npm ci` e ao build do frontend.
O CSS compilado e as cópias de HTMX e Alpine.js são versionados, portanto a
imagem Docker de produção não precisa instalar Node.js.

### 2. Iniciar e preparar o banco

```bash
# Sobe somente o PostgreSQL em segundo plano.
docker compose up -d db

# Cria ou atualiza a estrutura das tabelas.
make migrate

# Cria a base fictícia mínima para explorar a aplicação.
make seed
```

Confirme a disponibilidade do banco com `docker compose ps`. O serviço `db`
precisa aparecer como saudável antes de `make migrate` ou `make test`.

`make seed` é idempotente e incremental: cria oito computadores fictícios, os
três turnos iniciais, uma política de reservas e a configuração padrão de
relatórios somente quando estão ausentes. Ele não sobrescreve descrições, notas,
estados operacionais, turnos editados/desativados nem versões encerradas.

Para obter uma massa histórica destinada aos relatórios, use:

```bash
make seed-reports
```

Esse comando executa o reset explícito dos próprios dados demonstrativos de
relatório. Use-o exclusivamente em banco descartável de desenvolvimento.

### 3. Iniciar e verificar a aplicação

```bash
make run
```

Mantenha esse terminal aberto; `Ctrl+C` encerra o servidor. Depois, valide:

- aplicação: <http://localhost:8000/>;
- health check: <http://localhost:8000/api/health/>;
- OpenAPI: <http://localhost:8000/api/docs/>.

O seletor inicial permite entrar com perfis fictícios. Usuário da Sala, Monitor
da Sala e Supervisor da Biblioteca possuem áreas funcionais; a seleção não é
autenticação real.

## Configuração de ambiente

O Compose e os comandos `make` carregam o `.env` da raiz. As variáveis mais
úteis no desenvolvimento local são:

- `POSTGRES_DB`, `POSTGRES_USER` e `POSTGRES_PASSWORD`: identificam o banco
  criado pelo Compose;
- `POSTGRES_HOST` e `POSTGRES_PORT`: informam ao Django onde alcançá-lo;
- `DJANGO_SETTINGS_MODULE`: normalmente permanece como
  `config.settings.local`.

Se a porta `5432` já estiver em uso, altere `POSTGRES_PORT` para uma porta livre,
como `5433`, antes de iniciar o banco. Essa é a porta exposta no computador; o
PostgreSQL continua em `5432` dentro da rede Docker.

Problemas frequentes:

- `python: command not found`: ative o ambiente com
  `source .venv/bin/activate`;
- erro de conexão ao PostgreSQL: execute `docker compose ps`, aguarde o health
  check e confira os valores `POSTGRES_*` do `.env`;
- porta ocupada: ajuste `POSTGRES_PORT` e reinicie somente o serviço `db`.

## Reconciliação de prazos

Antes de uma consulta operacional autorizada, a aplicação reconcilia somente os
usuários, computadores ou período que a resposta observará. Assim, uma rodada
periódica atrasada não deixa a interface mostrar estado vencido.

O processo periódico continua obrigatório para atualizar os dados mesmo sem
acessos. O comando abaixo executa uma única rodada: cancela reservas cujo
check-in venceu e registra automaticamente a saída de sessões que chegaram ao
prazo máximo.

```bash
cd backend && python manage.py reconcile_operational_deadlines
```

O comando é idempotente e pode ser executado manualmente para testar esse fluxo.
Não depende de fila assíncrona.

Para manter a reconciliação em execução contínua, use o modo `--watch`, que
repete a rodada a cada 60 segundos, registra falhas em `stderr` e tenta
novamente no ciclo seguinte:

```bash
make reconcile-watch
```

No Docker, o serviço `scheduler` do `compose.yaml` executa esse mesmo modo com
`restart: unless-stopped`:

```bash
docker compose up -d db
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py seed_demo_data
docker compose up -d web scheduler
```

A ordem obrigatória em ambos os ambientes é banco → migrations → seed →
aplicação e processo periódico. O processo periódico depende apenas do banco e
encerra normalmente com `Ctrl+C` no host.

## Execução integral com Docker

Se preferir não instalar Python e Node.js no host, o Compose também executa a
aplicação inteira. Prepare o banco antes de iniciar a aplicação e o agendador:

```bash
docker compose build
docker compose up -d db
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py seed_demo_data
docker compose up -d web scheduler
```

Acesse <http://localhost:8000/> normalmente. Para acompanhar o servidor, use
`docker compose logs -f web`; para encerrar os containers, use
`docker compose down`. O serviço `scheduler` mantém a reconciliação periódica
ativa enquanto o ambiente estiver em execução.

## Comandos de qualidade

```bash
make check
make lint
make format-check
make test
```

Use-os com o ambiente virtual ativo e o banco `db` saudável. Para a validação
completa antes de enviar alterações, rode também:

```bash
npm ci
npm run build
cd backend && python manage.py spectacular --file /tmp/schema.yml --validate --fail-on-warn
git diff --check
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

## Seeds de demonstração

`seed_demo_data` é incremental e não destrutivo: cria computadores canônicos ausentes, cria os três turnos somente quando não existe nenhum turno e cria o calendário regular somente quando não existe nenhuma versão regular. Reexecuções nunca restauram descrições, notas, estados operacionais, turnos editados/desativados nem versões encerradas. O reset explícito de `seed_report_demo_data --reset` mantém seu comportamento próprio e deve ser usado apenas em banco descartável de desenvolvimento.

Consulte [../architecture/08-estado-implementacao.md](../architecture/08-estado-implementacao.md) para o detalhamento do que já foi entregue.
