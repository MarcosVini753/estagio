# Documentação do sistema

Esta pasta concentra a documentação funcional, arquitetural, operacional e histórica do Sistema de Controle de Uso da Sala de Informática da Biblioteca da UFAC.

## Comece por aqui

- [Guia rápido](guia-rapido.md) — entenda o sistema em 5 minutos.
- [Visão geral do produto](product/00-visao-geral.md) — problema, objetivo, atores e restrições.
- [Regras de negócio](product/03-regras-de-negocio.md) — as regras funcionais completas.

## Trilhas de leitura

### Quero entender o produto

1. [Guia rápido](guia-rapido.md)
2. [Visão geral do produto](product/00-visao-geral.md)
3. [Escopo do MVP](product/01-escopo-mvp.md)
4. [Regras de negócio](product/03-regras-de-negocio.md)
5. [Casos de uso e fluxos](product/04-casos-de-uso-e-fluxos.md)

### Quero desenvolver

1. [Configuração do backend](development/backend-setup.md)
2. [Visão geral da arquitetura](architecture/00-visao-geral.md)
3. [Modelo de domínio](architecture/02-modelo-de-dominio.md)
4. [Disponibilidade e agendamento](architecture/03-disponibilidade-e-agendamento.md)
5. [API](architecture/04-api.md)
6. [Integração contínua](development/ci.md)
7. [Estado da implementação](architecture/08-estado-implementacao.md)

### Quero manter ou evoluir

1. [Decisões arquiteturais (ADRs)](adr/README.md)
2. [Diagramas](diagrams/README.md)
3. [Skills e regras para agentes](development/agent-skills.md)
4. [Integração contínua](development/ci.md)
5. [Instruções para agentes](../AGENTS.md)

## Estrutura

```text
docs/
├── guia-rapido.md          # visão geral em 5 minutos
├── product/                # escopo, atores, regras, fluxos e glossário
├── architecture/           # arquitetura, módulos, domínio, API e relatórios
│   └── diagrams/           # C4, módulos e ERD
├── development/            # setup, CI e uso de agentes
├── adr/                    # decisões arquiteturais
└── diagrams/               # casos de uso e atividades em PlantUML
```

## Regras de manutenção

- Mudança funcional atualiza `product/`.
- Mudança estrutural atualiza `architecture/` e pode exigir ADR.
- Mudança de frontend deve respeitar a ADR 0023.
- O OpenAPI gerado é o contrato executável da API.
- Skills e regras de agentes não podem contradizer `AGENTS.md`.
- O protótipo é referência visual, não fonte de banco, segurança ou arquitetura.
- Mudanças devem manter os checks documentados em `development/ci.md` executáveis.
