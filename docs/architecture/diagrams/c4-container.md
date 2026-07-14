# C4 — Contêineres

```mermaid
flowchart TB
    browser[Navegador]
    web[Django Web
Templates + JavaScript]
    api[API REST /api/v1/
Django REST Framework]
    services[Serviços de domínio]
    reports[Consultas e projeções]
    db[(PostgreSQL)]
    admin[Django Admin futuro]

    browser --> web
    web --> api
    api --> services
    api --> reports
    services --> db
    reports --> db
    admin --> services
```

## Responsabilidades

- Django Web: entrega páginas, assets e seletor de perfil.
- API: contrato versionado para operações e consultas.
- Serviços: garantem invariantes e transações.
- Projeções: calculam relatórios sem persistir totais manuais.
- PostgreSQL: fonte de verdade operacional.
- Django Admin: reservado para administração futura.
