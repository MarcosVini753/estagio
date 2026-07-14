# Instruções para agentes de código

Este repositório documenta e implementará o Sistema de Controle de Uso da Sala de Informática da Biblioteca da UFAC.

## Fontes de verdade

Consulte os documentos nesta ordem:

1. `docs/product/`: escopo, atores, regras e fluxos funcionais.
2. `docs/architecture/`: arquitetura vigente, módulos, modelo de domínio, API e relatórios.
3. `docs/adr/`: decisões arquiteturais e justificativas.
4. `docs/diagrams/`: diagramas UML já validados.
5. `prototipos/`: referência visual e comportamental, não fonte de modelagem ou segurança.

Em caso de conflito, a ordem acima prevalece. ADRs registram decisões; os documentos de arquitetura descrevem o estado corrente.

## Invariantes funcionais

- Não implementar fila de espera.
- A consulta de disponibilidade é limitada a hoje e amanhã.
- Hoje permite uso imediato em horários que ainda não passaram.
- Reserva antecipada é permitida somente para amanhã.
- O computador persiste apenas estado operacional: `AVAILABLE`, `MAINTENANCE` ou `INACTIVE`.
- `OCCUPIED` e `RESERVED` são estados calculados para um instante ou intervalo.
- Um usuário pode possuir no máximo uma sessão ativa.
- Um computador pode possuir no máximo uma alocação ativa.
- Uma sessão pode conter várias alocações por causa da troca de computador.
- Trocar de computador não cria uma nova sessão e não apaga o histórico anterior.
- Relatórios são projeções calculadas; não criar lançamentos manuais de relatório.
- O ator operacional é denominado `Estagiário`, não `Servidor da Biblioteca`.
- O Administrador do Sistema existe na arquitetura, embora seus casos de uso detalhados estejam adiados.

## Autenticação da primeira versão

- Não existe autenticação real no MVP inicial.
- A interface apresenta uma tela para escolher o perfil de teste.
- O perfil selecionado determina menus e autorizações simuladas.
- Não adicionar senha, JWT, OAuth, SSO ou integração institucional sem novo ADR.
- A autorização simulada não oferece segurança e só pode ser usada com dados fictícios em ambiente local ou controlado.

## Direção técnica

- Backend em Django e Django REST Framework.
- Monólito modular organizado em apps por domínio.
- API versionada em `/api/v1/`.
- Frontend inicial com Django Templates e JavaScript puro, preservando o protótipo como referência.
- PostgreSQL é o banco-alvo.
- OpenAPI deve acompanhar a implementação da API.

## Regras para alterações

- Mudança arquitetural relevante exige ADR novo ou substituição explícita de ADR anterior.
- Mudança de regra funcional exige atualização em `docs/product/`.
- Mudança de endpoint exige atualização em `docs/architecture/04-api-v1.md`, OpenAPI e testes.
- Toda regra crítica deve possuir teste automatizado.
- Não introduzir microsserviços, Redis, Celery, WebSockets, JWT ou frontend SPA sem justificativa e ADR.
- Não duplicar regra de negócio em views, serializers e modelos; centralize operações em serviços de domínio.
- Não confiar no estado armazenado pelo protótipo em `localStorage` como modelo do banco.
