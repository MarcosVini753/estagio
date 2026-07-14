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
- O ator operacional é `Estagiário`, não `Servidor da Biblioteca`.
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
- API versionada em `/api/v1/`.
- Django Templates e JavaScript puro.
- OpenAPI com `drf-spectacular`.
- Configurações separadas para local, testes e produção.

## Estado de implementação

As etapas 2 e 3 possuem scaffold Django, modelos, migrations, autorização simulada, CI, CRUD inicial de computadores e configurações, histórico de estado operacional, geração de slots e consulta de disponibilidade para hoje e amanhã.

Ainda não existem serviços completos para criar ou cancelar reservas, registrar entrada, trocar computador, registrar saída, tratar ocorrências ou gerar relatórios. Essas funcionalidades devem ser implementadas em fatias verticais, sem concentrar regras em views ou serializers.

## Implementação mínima e correta

1. confirme a necessidade da alteração;
2. procure padrões reutilizáveis;
3. prefira Python, Django, DRF e PostgreSQL a código próprio;
4. não crie abstrações para necessidades hipotéticas;
5. mantenha regras transacionais em serviços de domínio;
6. mantenha consultas complexas e projeções em selectors;
7. use constraints para invariantes persistentes;
8. atualize migrations, testes, OpenAPI e documentação quando aplicável.

## Skills e qualidade

As skills ficam em `.cline/skills/`. Antes de concluir, execute:

```bash
make check
make lint
make format-check
make test
```

Mudanças arquiteturais exigem ADR. Mudanças funcionais atualizam `docs/product/`. Mudanças de endpoint atualizam OpenAPI, `docs/architecture/04-api-v1.md` e testes.
