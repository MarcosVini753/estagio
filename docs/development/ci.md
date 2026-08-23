# Integração contínua

O repositório usa GitHub Actions para validar alterações antes de integração entre branches.

## Workflow principal

O workflow `.github/workflows/backend.yml` usa o nome `Continuous Integration` e executa em:

- todo `push` para qualquer branch;
- todo `pull_request`;
- execução manual por `workflow_dispatch`.

Não há filtro por caminho. Assim, os mesmos status checks aparecem de forma consistente independentemente do tipo de alteração.

A execução usa `concurrency` por referência e cancela uma execução anterior ainda em andamento quando um novo commit é enviado para a mesma branch.

## Checks

### Quality checks

Valida a aplicação com PostgreSQL 17, Python 3.14 e Node.js 22:

1. instala `requirements/dev.txt` e as dependências bloqueadas pelo `package-lock.json`;
2. recompila Tailwind CSS, HTMX e Alpine.js e falha se os assets versionados gerarem diff;
3. executa `python manage.py check`;
4. verifica drift de migrations com `makemigrations --check --dry-run`;
5. aplica migrations em um banco PostgreSQL limpo;
6. executa a suíte de testes Django;
7. gera e valida o OpenAPI com warnings fatais;
8. executa `ruff check` e `ruff format --check`.

### Container build

Executa um build real da imagem definida em `backend/Dockerfile` usando o contexto da raiz do repositório.

A imagem é construída apenas para validação. A CI não publica imagens e não faz deploy.

### Frontend end-to-end

Valida a interface Django real em um ambiente efêmero:

1. provisiona PostgreSQL, Python, Node.js, Playwright e Chromium;
2. compila os assets, aplica migrations e executa `seed_demo_data`;
3. inicia o servidor Django real;
4. seleciona o Usuário da Sala com identidade fictícia e valida layout, navegação e gestos em mobile e desktop;
5. seleciona o Monitor da Sala em viewport mobile, acessa ocorrências e registra um problema real;
6. seleciona o Supervisor da Biblioteca em desktop e percorre inventário, configurações e relatório mensal;
7. testa swipe entre hoje e amanhã, swipe da navegação inferior e distinção de rolagem vertical;
8. falha caso existam erros JavaScript não tratados no navegador.

O job possui limite de 15 minutos. Em `ubuntu-latest`, ele baixa somente o
binário Chromium compatível com a versão bloqueada do Playwright; não executa
`--with-deps` nem instala pacotes do sistema via `apt`. Isso evita que a
infraestrutura de pacotes do runner domine o tempo do teste E2E.

## Deploy não é CI

`.github/workflows/static.yml` continua responsável somente pelo deploy do protótipo no GitHub Pages e permanece restrito à `main`.

Branches de feature não devem fazer deploy de produção apenas por receberem novos commits.

## Branches existentes

Branches criadas a partir de uma `dev` que já contém o workflow herdam a configuração automaticamente.

Uma branch antiga que ainda não contém essa versão do workflow precisa incorporar as mudanças de `dev` para receber os checks em eventos de `push`. Pull requests continuam sendo a fronteira recomendada de integração e devem ser validados antes de merge.

## Proteção de branches

Depois que os três checks tiverem executado ao menos uma vez com seus nomes definitivos, recomenda-se configurar `dev` e `main` como branches protegidas e exigir antes de merge:

- `Continuous Integration / Quality checks`;
- `Continuous Integration / Container build`;
- `Continuous Integration / Frontend end-to-end`.

A proteção é configuração do repositório no GitHub, não parte do arquivo YAML.

## Evolução esperada

Com o frontend da ADR 0023 implementado para Usuário da Sala, Monitor e Supervisor, a CI deve evoluir sem criar pipelines paralelos desnecessários:

- adicionar type-check somente se TypeScript for adotado;
- manter testes de backend e frontend independentes o suficiente para identificar a origem de falhas;
- ampliar o E2E quando a interface própria do Administrador for migrada;
- adicionar verificações de segurança e imagem de produção apenas quando o deploy real estiver sendo preparado.
