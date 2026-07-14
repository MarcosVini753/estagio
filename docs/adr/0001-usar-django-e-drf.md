# ADR 0001: Usar Django e Django REST Framework

## Status

Aceita

## Contexto

O sistema precisa persistir computadores, reservas, sessões, alocações, ocorrências, configurações e relatórios, além de expor uma API para o frontend.

## Decisão

Usar Django como framework principal e Django REST Framework para a API versionada.

## Alternativas consideradas

- FastAPI;
- Node.js com Express ou NestJS;
- aplicação somente frontend;
- Django sem DRF.

## Consequências positivas

- ORM, migrations e transações integrados;
- suporte futuro a usuários, grupos, permissões e Admin;
- estrutura adequada para monólito modular;
- ecossistema maduro para OpenAPI e testes.

## Consequências negativas e riscos

- exige disciplina na separação entre apps, serviços e serializers;
- regras não devem ficar dispersas em views ou signals;
- a equipe precisa evitar usar o Django Admin como interface principal dos usuários da sala.
