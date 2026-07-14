# Documentação do sistema

Esta pasta concentra a documentação funcional, arquitetural, operacional e histórica do Sistema de Controle de Uso da Sala de Informática da Biblioteca da UFAC.

## Estrutura

```text
docs/
├── product/              # escopo, atores, regras, fluxos e glossário
├── architecture/         # arquitetura, módulos, domínio, API e relatórios
│   └── diagrams/         # C4, módulos e ERD
├── development/          # setup do backend e uso de agentes
├── adr/                  # decisões arquiteturais
└── diagrams/             # casos de uso e atividades em PlantUML
```

## Ordem de leitura

1. [Visão geral do produto](product/00-visao-geral.md)
2. [Escopo do MVP](product/01-escopo-mvp.md)
3. [Regras de negócio](product/03-regras-de-negocio.md)
4. [Visão geral da arquitetura](architecture/00-visao-geral.md)
5. [Módulos](architecture/01-modulos.md)
6. [Modelo de domínio](architecture/02-modelo-de-dominio.md)
7. [API v1](architecture/04-api-v1.md)
8. [Estado da implementação](architecture/08-estado-implementacao.md)
9. [Índice de ADRs](adr/README.md)

## Guias

- [Configuração inicial do backend](development/backend-setup.md)
- [Skills para Cline e Codex](development/agent-skills.md)

## Regras de manutenção

- Mudança funcional atualiza `product/`.
- Mudança estrutural atualiza `architecture/` e pode exigir ADR.
- O OpenAPI gerado é o contrato executável da API.
- Skills e regras de agentes não podem contradizer `AGENTS.md`.
- O protótipo é referência visual, não fonte de banco, segurança ou arquitetura.

## Estado atual

O scaffold Django, os apps, os modelos e as migrations iniciais já existem. Os endpoints implementados nesta etapa são o health check e o contexto de demonstração. Os fluxos operacionais serão implementados incrementalmente nas próximas etapas.
