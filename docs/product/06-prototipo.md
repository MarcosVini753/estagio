# Protótipo navegável

O diretório `prototipos/` contém a referência visual original em HTML, CSS e JavaScript puro.

## Finalidade

- validar navegação e hierarquia visual;
- demonstrar os fluxos dos perfis;
- apoiar validação com a biblioteca;
- orientar a migração para o frontend definitivo em Django Templates, HTMX, Alpine.js e Tailwind CSS.

## Não inferir do protótipo

- objetos de `localStorage` não definem o banco;
- `statusToday`, `statusTomorrow`, `busy` e `reserved` não são campos persistidos;
- escolha de perfil não é autenticação;
- dados simulados não representam pessoas reais;
- regras somente no frontend devem ser reimplementadas no backend;
- a estrutura atual de arquivos CSS e JavaScript não define a arquitetura final do frontend.

## Estratégia de migração

A ADR 0023 substitui a estratégia anterior de Django Templates com JavaScript puro por uma abordagem de progressive enhancement:

- Django Templates compõem páginas, componentes e partials;
- HTMX executa interações que precisam do servidor e atualiza apenas os trechos necessários;
- Alpine.js controla somente estado local e efêmero de interface;
- Tailwind CSS 4 fornece a base de estilos e do design system;
- JavaScript ou TypeScript adicional deve ser pontual e justificado;
- a API `/api/` continua disponível como contrato do backend;
- regras de domínio não devem ser duplicadas no navegador.

A migração é incremental. Os fluxos do Usuário da Sala, Monitor da Sala e Supervisor da Biblioteca já foram reproduzidos no frontend Django; o protótipo permanece como referência histórica e para a interface ainda não migrada do Administrador.

## Ajustes durante a integração

- não introduzir fila de espera;
- usar Monitor da Sala, não Servidor da Biblioteca;
- separar estado operacional de estado efetivo;
- permitir reserva de slots consecutivos para horário futuro de hoje ou para amanhã;
- informar a janela de entrada por reserva, de três minutos antes do início até três minutos depois;
- permitir uso imediato somente hoje, com saída planejada escolhida antes da entrada;
- exibir fim planejado, sem expor o prazo operacional de saída;
- impedir intervalo que atravesse reserva ou fechamento;
- impedir horários passados;
- substituir agregados simulados por sessões e alocações;
- substituir gradualmente `localStorage` por estado vindo do backend;
- usar respostas do backend para disponibilidade, limites de sessão e transições de estado;
- manter a experiência mobile-first;
- preparar a estrutura para PWA futura, sem exigir funcionamento offline nesta etapa.

## Estado atual

O seletor dos quatro perfis e as áreas funcionais do Usuário da Sala, Monitor da Sala e Supervisor da Biblioteca estão implementados no app Django `web`. Os fluxos usam dados e serviços reais do backend, preservam navegação convencional como alternativa a HTMX e Alpine.js e mantêm o perfil de demonstração visível.

O Administrador continua exibindo uma página coerente de indisponibilidade. A CI compila os assets versionados e executa o E2E contra a aplicação Django real, com PostgreSQL, migrations e seed, cobrindo os três perfis migrados em mobile e desktop.
