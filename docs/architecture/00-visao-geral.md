# Visão geral da arquitetura

## Estilo

Monólito modular em Django, com uma aplicação implantável e um banco PostgreSQL.

```text
Navegador
├── Django Templates
├── HTMX para interações com o servidor
├── Alpine.js para estado local de interface
├── Tailwind CSS para apresentação
├── login por CPF/matrícula e senha
└── documentação OpenAPI
        │
        ▼
Django + DRF
├── páginas e partials HTML
├── API /api/
├── serviços de domínio
├── selectors e projeções
└── autenticação por sessão Django e autorização pelo perfil da conta
        │
        ▼
PostgreSQL
```

## Stack

- Python 3.14;
- Django 5.2 LTS;
- Django REST Framework;
- PostgreSQL 17;
- Django Templates como base do frontend;
- HTMX para atualização parcial orientada pelo servidor;
- Alpine.js para estado visual e efêmero;
- Tailwind CSS 4 para estilos e design system;
- JavaScript e TypeScript de forma seletiva quando necessário;
- Chart.js para gráficos gerenciais quando essas telas forem implementadas;
- `drf-spectacular`;
- Docker Compose;
- Ruff;
- GitHub Actions.

A stack de frontend acima está implementada para a área do Usuário da Sala, conforme a ADR 0023. O protótipo em `prototipos/` continua como referência visual para as interfaces dos demais perfis e não representa a implementação final.

## Apps

- `core`;
- `web`;
- `access`;
- `configuration`;
- `computers`;
- `operations`;
- `occurrences`;
- `reports`;
- `audit`.

## Camadas

- apresentação: Django Templates, partials, HTMX, Alpine.js, estilos, views e serializers;
- aplicação: serviços que executam casos de uso;
- domínio: models, enums, constraints e políticas;
- consulta: selectors, projeções e exportadores;
- infraestrutura: ORM, PostgreSQL, sessões, OpenAPI e pipeline de CI.

## Princípios

- regras não dependem do frontend;
- o backend é a fonte de verdade para disponibilidade, reservas, sessões e transições de estado;
- operações críticas são transacionais;
- estados calculados não são persistidos;
- relatórios consultam dados operacionais;
- a identidade autenticada e o perfil vêm da conta persistida, nunca do payload ou de chaves de demonstração na sessão;
- não existe integração institucional/SSO, autocadastro ou conta para `SYSTEM_ADMIN`;
- credenciais compartilhadas de demonstração só podem ser usadas com dados fictícios em ambiente local/controlado;
- HTML e JavaScript devem seguir progressive enhancement;
- uma SPA separada exige nova decisão arquitetural.

## Integração frontend/backend

HTMX deve ser preferido quando uma interação precisa executar lógica no servidor e atualizar somente parte da página. Alpine.js deve permanecer restrito a comportamento local que não representa estado de domínio.

A API `/api/` continua sendo contrato executável para clientes externos. As views HTML reutilizam serializers de entrada, selectors e serviços de domínio no mesmo processo Django, sem chamadas HTTP internas. Não duplicar no navegador cálculos ou validações já disponíveis no backend.

A interface deve ser mobile-first e preparada para evolução posterior para PWA, sem tornar funcionamento offline um requisito atual.

## Estado atual

O scaffold, apps, modelos, migrations, Compose, CI, health check e login local
com contas persistidas estão implementados. Os serviços operacionais e endpoints de
domínio também já existem: reservas, sessões, troca de computador, saída,
ocorrências, calendário operacional, indisponibilidade de computador e
relatórios diário, mensal, anual e de indicadores com exportação.

O app `access` autentica CPF ou matrícula com senha e mantém sessão Django; o perfil deriva da conta e não pode ser escolhido na tela. O seed local/teste cria três contas fictícias e não cria nem permite conta `SYSTEM_ADMIN`. O app de apresentação `web` entrega as áreas funcionais do Usuário da Sala, Monitor da Sala e Supervisor da Biblioteca com Django Templates, HTMX, Alpine.js e Tailwind CSS. A integração institucional e a administração própria permanecem fora do escopo. Consulte `08-estado-implementacao.md` para o detalhamento.
