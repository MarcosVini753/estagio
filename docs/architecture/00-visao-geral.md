# Visão geral da arquitetura

## Estilo

Monólito modular em Django, com uma aplicação implantável e um banco PostgreSQL.

```text
Navegador
├── Django Templates e JavaScript
├── seletor de perfil de teste
└── documentação OpenAPI
        │
        ▼
Django + DRF
├── API /api/v1/
├── serviços de domínio
├── selectors e projeções
└── autorização simulada em sessão
        │
        ▼
PostgreSQL
```

## Stack

- Python 3.12;
- Django 5.2 LTS;
- Django REST Framework;
- PostgreSQL 17;
- Django Templates e JavaScript puro;
- `drf-spectacular`;
- Docker Compose;
- Ruff;
- GitHub Actions.

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

- apresentação: templates, JavaScript, views e serializers;
- aplicação: serviços que executam casos de uso;
- domínio: models, enums, constraints e políticas;
- consulta: selectors, projeções e exportadores;
- infraestrutura: ORM, PostgreSQL, sessões e OpenAPI.

## Princípios

- regras não dependem do frontend;
- operações críticas são transacionais;
- estados calculados não são persistidos;
- relatórios consultam dados operacionais;
- autorização simulada não é identidade;
- não existe Django Admin ou autenticação real no MVP.

## Estado atual

O scaffold, apps, modelos, migrations, Compose, CI, health check e contexto de demonstração estão implementados. Os serviços operacionais e endpoints de domínio permanecem pendentes.
