# Visão geral da arquitetura

## Estilo

Monólito modular em Django, com uma aplicação implantável e um banco PostgreSQL.

```text
Navegador
├── Django Templates
├── HTMX para interações com o servidor
├── Alpine.js para estado local de interface
├── Tailwind CSS para apresentação
├── seletor de perfil de teste
└── documentação OpenAPI
        │
        ▼
Django + DRF
├── páginas e partials HTML
├── API /api/
├── serviços de domínio
├── selectors e projeções
└── autorização simulada em sessão
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

A stack de frontend acima é a arquitetura alvo definida na ADR 0023. O protótipo em `prototipos/` ainda usa HTML, CSS e JavaScript puro e não representa a implementação final.

## Apps

- `core`;
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
- autorização simulada não é identidade;
- não existe Django Admin ou autenticação real no MVP;
- HTML e JavaScript devem seguir progressive enhancement;
- uma SPA separada exige nova decisão arquitetural.

## Integração frontend/backend

HTMX deve ser preferido quando uma interação precisa executar lógica no servidor e atualizar somente parte da página. Alpine.js deve permanecer restrito a comportamento local que não representa estado de domínio.

A API `/api/` continua sendo contrato executável e pode ser consumida diretamente quando isso simplificar uma interação. Não duplicar no navegador cálculos ou validações já disponíveis no backend.

A interface deve ser mobile-first e preparada para evolução posterior para PWA, sem tornar funcionamento offline um requisito atual.

## Estado atual

O scaffold, apps, modelos, migrations, Compose, CI, health check e contexto de demonstração estão implementados. Os serviços operacionais e endpoints de domínio também já existem: reservas, sessões, troca de computador, saída, ocorrências, calendário operacional, indisponibilidade de computador e relatório mensal. Consulte `08-estado-implementacao.md` para o detalhamento.

A implementação do frontend definitivo ainda não começou. O próximo passo de interface é migrar progressivamente o protótipo para Django Templates seguindo a ADR 0023.
