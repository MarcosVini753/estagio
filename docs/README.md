# Documentação do sistema

Esta pasta concentra a documentação funcional, arquitetural, operacional e histórica do Sistema de Controle de Uso da Sala de Informática da Biblioteca da UFAC.

## Estrutura

```text
docs/
├── README.md
├── product/
│   ├── 00-visao-geral.md
│   ├── 01-escopo-mvp.md
│   ├── 02-atores-e-permissoes.md
│   ├── 03-regras-de-negocio.md
│   ├── 04-casos-de-uso-e-fluxos.md
│   ├── 05-glossario.md
│   └── 06-prototipo.md
├── architecture/
│   ├── 00-visao-geral.md
│   ├── 01-modulos.md
│   ├── 02-modelo-de-dominio.md
│   ├── 03-disponibilidade-e-agendamento.md
│   ├── 04-api-v1.md
│   ├── 05-autorizacao-simulada.md
│   ├── 06-relatorios.md
│   ├── 07-auditoria-e-testes.md
│   └── diagrams/
│       ├── c4-context.md
│       ├── c4-container.md
│       ├── module-map.md
│       └── erd.md
├── development/
│   └── agent-skills.md
├── adr/
└── diagrams/
```

## Como usar

- `product/` descreve o que o sistema deve fazer.
- `architecture/` descreve como a solução está organizada atualmente.
- `development/` contém procedimentos de desenvolvimento e uso de ferramentas.
- `adr/` registra decisões, alternativas e consequências.
- `diagrams/` contém os diagramas UML de casos de uso e atividades.
- `prototipos/` permanece na raiz como referência navegável de interface.

## Guias

- [Instalação e uso de skills no Cline e Codex](development/agent-skills.md)

## Regras de manutenção

1. Mudanças funcionais devem atualizar `product/`.
2. Mudanças estruturais devem atualizar `architecture/` e, quando relevantes, gerar ADR.
3. A documentação arquitetural deve refletir o estado atual, mesmo quando um ADR antigo tiver sido substituído.
4. O contrato OpenAPI gerado pelo backend será a fonte executável da API; `04-api-v1.md` explica sua organização e semântica.
5. Skills e regras de agentes devem ser revisadas por pull request e não podem contradizer `AGENTS.md`.

## Estado atual

O projeto possui requisitos, diagramas PlantUML e protótipo em HTML, CSS e JavaScript puro. A próxima fase é inicializar o monólito Django, implementar o modelo de domínio e substituir gradualmente o estado simulado do protótipo por chamadas à API `/api/v1/`.
