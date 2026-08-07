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

Valida o backend com PostgreSQL 17 e Python 3.14:

1. instala `requirements/dev.txt`, com cache de `pip`;
2. executa `python manage.py check`;
3. verifica drift de migrations com `makemigrations --check --dry-run`;
4. aplica migrations em um banco PostgreSQL limpo;
5. executa a suíte de testes Django;
6. gera e valida o OpenAPI com `drf-spectacular`;
7. executa `ruff check`;
8. executa `ruff format --check`.

### Container build

Executa um build real da imagem definida em `backend/Dockerfile` usando o contexto da raiz do repositório.

A imagem é construída apenas para validação. A CI não publica imagens e não faz deploy.

### Frontend end-to-end

Enquanto o frontend definitivo ainda não foi migrado para Django Templates, a CI valida o protótipo navegável:

1. instala Playwright e Chromium em ambiente efêmero;
2. inicia um servidor HTTP local para `prototipos/`;
3. abre a interface em um navegador headless;
4. confirma que a página inicial carrega sem erro;
5. confirma que o JavaScript inicializa a tela;
6. executa uma interação real de troca de `Hoje` para `Amanhã`;
7. falha caso existam erros JavaScript não tratados no navegador.

Quando a interface Django for implementada, esse job deve passar a inicializar a aplicação real e testar os fluxos prioritários do usuário, em vez do protótipo estático.

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

Com a implementação do frontend da ADR 0023, a CI deve evoluir sem criar pipelines paralelos desnecessários:

- adicionar build de Tailwind quando a dependência entrar no projeto;
- adicionar type-check somente se TypeScript for adotado;
- migrar o E2E do protótipo para a aplicação Django real;
- manter testes de backend e frontend independentes o suficiente para identificar a origem de falhas;
- adicionar verificações de segurança e imagem de produção apenas quando o deploy real estiver sendo preparado.
