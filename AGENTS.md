# Instruções para agentes de código

Este repositório documenta e implementa o Sistema de Controle de Uso da Sala de Informática da Biblioteca da UFAC.

## Fontes de verdade

Consulte nesta ordem:

1. `docs/product/`: escopo, atores, regras e fluxos funcionais.
2. `docs/architecture/`: arquitetura vigente, módulos, modelo de domínio, API e relatórios.
3. `docs/adr/`: decisões arquiteturais e justificativas.
4. `docs/diagrams/`: diagramas UML validados.
5. `prototipos/`: referência visual e comportamental, não fonte de modelagem ou segurança.

Em caso de conflito, a ordem acima prevalece. ADRs registram decisões; os documentos de arquitetura descrevem o estado corrente.

## Invariantes funcionais

- Não implementar fila de espera.
- A consulta de disponibilidade é limitada a hoje e amanhã.
- Hoje permite uso imediato em horários que ainda não passaram.
- Reservas podem ser criadas para horários futuros de hoje ou para amanhã.
- O computador persiste apenas `AVAILABLE`, `MAINTENANCE` ou `INACTIVE`.
- `OCCUPIED` e `RESERVED` são calculados para um instante ou intervalo.
- Um usuário pode possuir no máximo uma sessão ativa.
- Um computador pode possuir no máximo uma alocação ativa.
- Uma sessão pode conter várias alocações por causa da troca de computador.
- Trocar de computador não cria nova sessão nem apaga histórico.
- Relatórios são projeções; não criar lançamentos manuais de relatório.
- O ator operacional é `Monitor da Sala`.
- O Administrador do Sistema existe arquiteturalmente, mas não possui autenticação real nesta etapa.

## Autorização da primeira versão

- Não existe autenticação real no MVP inicial.
- A interface apresenta uma tela para escolher o perfil de teste.
- O perfil selecionado é armazenado na sessão Django e controla autorizações simuladas.
- Não adicionar senha, Django Admin, JWT, OAuth, SSO ou integração institucional sem novo ADR.
- O modo de demonstração não oferece segurança e só pode usar dados fictícios em ambiente local ou controlado.

## Direção técnica

- Backend em Django 5.2 LTS e Django REST Framework.
- Monólito modular em apps por domínio.
- PostgreSQL como banco-alvo.
- API exposta em `/api/`, sem versão no caminho.
- Frontend em Django Templates com progressive enhancement.
- HTMX para interações orientadas pelo servidor.
- Alpine.js somente para estado local e efêmero de interface.
- Tailwind CSS 4 como base de estilos quando a migração do frontend começar.
- JavaScript ou TypeScript adicional somente quando necessário; não criar SPA sem novo ADR.
- Chart.js é a opção prevista para gráficos gerenciais.
- OpenAPI com `drf-spectacular`.
- Configurações separadas para local, testes e produção.

## Implementação mínima e correta

Aplique o princípio Ponytail depois de compreender integralmente a tarefa e o fluxo afetado:

1. confirme se a alteração realmente precisa existir;
2. procure implementação ou padrão reutilizável no repositório;
3. prefira Python, Django, DRF ou PostgreSQL a código próprio;
4. prefira recursos nativos de HTML, HTMX, CSS e navegador a dependências;
5. mantenha regras transacionais em serviços de domínio;
6. mantenha consultas complexas e projeções em selectors;
7. use constraints para invariantes persistentes;
8. atualize migrations, testes, OpenAPI e documentação quando aplicável;
9. reutilize dependências já instaladas antes de adicionar outra;
10. escreva somente o mínimo necessário para atender corretamente à regra.

Não crie abstrações, camadas, dependências ou configurações para necessidades hipotéticas. O menor diff correto vence, mas minimalismo nunca pode remover validação, integridade, segurança, acessibilidade, auditoria, migrations ou testes exigidos pelo projeto.

No frontend, o backend é a fonte de verdade. Não replique em Alpine.js, JavaScript ou TypeScript regras de disponibilidade, reserva, duração de sessão, concorrência, autorização ou transições de estado.

## Skills e fluxo de qualidade

As skills específicas para Cline ficam em `.cline/skills/`. Use a mais adequada à tarefa. Antes de concluir, execute:

```bash
make check
make lint
make format-check
make test
```

- `django-feature-development` para funcionalidades completas;
- `django-model-and-migration` para esquema e migrations;
- `api-endpoint` para API DRF;
- `test-first-change` para bugs e mudanças críticas;
- `code-review` para revisão geral antes de merge;
- `ponytail-review` para uma segunda revisão focada em sobre-engenharia;
- `documentation-sync` para manter código e documentação coerentes.

A CI executa verificações de qualidade, build do container e teste E2E do frontend em branches. Consulte `docs/development/ci.md`.

Antes de concluir uma implementação, execute os comandos de qualidade disponíveis no repositório. Não declare a tarefa concluída quando testes, lint, migrations ou verificações obrigatórias falharem. Mudanças arquiteturais exigem ADR. Mudanças funcionais atualizam `docs/product/`. Mudanças de endpoint atualizam OpenAPI, `docs/architecture/04-api.md` e testes.
