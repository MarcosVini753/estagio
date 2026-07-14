# Sistema de Controle de Uso da Sala de Informática da Biblioteca da UFAC

Repositório de documentação, diagramas, protótipo navegável e futura implementação Django do sistema web de controle de uso da Sala de Informática da Biblioteca da UFAC.

## Estado atual

O projeto está na etapa de consolidação documental e arquitetural. Já existem:

- regras funcionais;
- casos de uso;
- diagramas de atividades;
- protótipo em HTML, CSS e JavaScript puro;
- arquitetura planejada para Django e Django REST Framework;
- modelo de domínio inicial;
- contrato preliminar da API `/api/v1/`;
- Architecture Decision Records;
- instruções e skills para agentes de código.

## Direção funcional consolidada

- consulta de disponibilidade somente para hoje e amanhã;
- uso imediato permitido hoje em horários ainda não passados;
- reserva antecipada permitida somente para amanhã;
- fila de espera fora do escopo;
- ator operacional denominado Estagiário;
- troca de computador preserva a mesma sessão e cria nova alocação;
- estados operacionais persistidos do computador: `AVAILABLE`, `MAINTENANCE` e `INACTIVE`;
- `OCCUPIED` e `RESERVED` são calculados;
- relatórios são projeções derivadas dos registros operacionais;
- autenticação real não existe no MVP inicial: o perfil é escolhido em uma tela de demonstração.

## Estrutura principal

```text
AGENTS.md
.clinerules/             # Regras persistentes do Cline
.cline/skills/           # Workflows especializados do Cline
README.md
docs/
├── README.md
├── product/             # Escopo, atores, regras, fluxos e glossário
├── architecture/        # Arquitetura vigente, módulos, domínio, API e relatórios
├── development/         # Procedimentos de desenvolvimento e agentes
├── adr/                 # Decisões arquiteturais
└── diagrams/            # Diagramas UML em PlantUML
prototipos/
├── README.md
├── index.html
├── css/
└── js/
```

## Documentação

- [Índice da documentação](docs/README.md)
- [Visão geral do produto](docs/product/00-visao-geral.md)
- [Escopo do MVP](docs/product/01-escopo-mvp.md)
- [Regras de negócio](docs/product/03-regras-de-negocio.md)
- [Visão geral da arquitetura](docs/architecture/00-visao-geral.md)
- [Modelo de domínio](docs/architecture/02-modelo-de-dominio.md)
- [API v1](docs/architecture/04-api-v1.md)
- [Índice de ADRs](docs/adr/README.md)
- [Índice dos diagramas](docs/diagrams/README.md)
- [Instruções para agentes](AGENTS.md)
- [Instalação e uso de skills no Cline e Codex](docs/development/agent-skills.md)

## Protótipo

Abra `prototipos/index.html` no navegador.

O protótipo utiliza `localStorage` e dados fictícios. Ele serve como referência visual e comportamental, não como fonte definitiva para banco de dados, segurança ou arquitetura.

## Próxima etapa

A próxima fase é inicializar o backend Django seguindo a documentação versionada:

1. criar a estrutura do projeto e dos apps;
2. configurar PostgreSQL, DRF e OpenAPI;
3. implementar computadores, turnos e disponibilidade;
4. implementar reservas, sessões e alocações;
5. implementar ocorrências e relatórios;
6. substituir gradualmente o estado simulado do protótipo pela API.
