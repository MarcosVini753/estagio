# Estado da implementação

## Concluído na etapa 2

- projeto Django e configurações por ambiente;
- PostgreSQL e Docker Compose;
- apps modulares;
- models e migrations iniciais;
- constraints básicas de sessão e alocação;
- health check;
- contexto de demonstração em sessão;
- tela mínima de seleção de perfil;
- OpenAPI, formato padronizado de erro, Ruff e CI.

## Concluído parcialmente na etapa 3

- endpoints de computadores;
- criação e edição de computadores pelo Supervisor ou Administrador;
- alteração de estado operacional pelo Monitor da Sala, Supervisor ou Administrador;
- histórico de mudanças do estado operacional;
- endpoints de turnos e exceções de calendário;
- consulta e versionamento da política de reservas;
- validação de sobreposição de turnos ativos;
- geração de slots fixos de 15 minutos a partir do calendário efetivo e exceções;
- consulta de disponibilidade somente para hoje ou amanhã;
- descarte de slots iniciados no passado;
- cálculo dos estados efetivos `OCCUPIED` e `RESERVED`;
- precedência de `INACTIVE` e `MAINTENANCE`;
- identificação de reserva pertencente ao usuário fictício atual;
- seed idempotente para o ambiente de demonstração;
- testes de API e regras de disponibilidade.
- criação, listagem e cancelamento transacionais de reservas;
- constraints PostgreSQL contra sobreposição de reservas confirmadas.
- entrada imediata e entrada vinculada a reserva;
- sessão atual, sessões ativas e histórico;
- troca de computador preservando a sessão;
- saída com encerramento da alocação atual;
- auditoria de saída operacional de terceiro.
- criação e consulta de ocorrências;
- vínculos coerentes com computador, sessão e alocação;
- transições e resolução de ocorrências por perfis operacionais.
- correção restrita de entrada, saída e último intervalo;
- auditoria e rollback integral de correções;
- constraint PostgreSQL contra sobreposição histórica de alocações.
- seed histórico determinístico e idempotente para relatórios;
- limpeza seletiva por prefixo e sentinelas `demo-report-`;
- sessões, trocas, reservas, ocorrências, manutenção e exceções de calendário fictícias.

## Concluído na Pré-Etapa 4

- contexto fictício ampliado para Usuário da Sala, com referência, vínculo e unidade institucional;
- snapshots de vínculo e unidade em reservas e sessões de uso;
- compatibilidade histórica para registros sem contexto, agrupáveis como `NOT_INFORMED`.
- versionamento futuro de turnos, com substituição auditada e preservação dos turnos já usados.
- identidade lógica compartilhada pelas versões do mesmo turno.
- relatório mensal JSON com matriz dia por turno lógico;
- métricas mensais derivadas de sessões, alocações, reservas e ocorrências;
- agrupamento `NOT_INFORMED`, calendário completo e recorte temporal de alocações.

## Concluído na entrega do calendário operacional

- calendário semanal regular versionado, com segunda a sexta 07h15–21h, sábado 07h15–13h e domingo fechado;
- horários temporários com início e fim e retorno automático ao regular;
- precedência de exceção pontual sobre temporário e regular;
- separação entre funcionamento da sala e turnos analíticos;
- status público da sala e contexto de fechamento nas respostas de disponibilidade;
- preview de reservas afetadas, confirmação e cancelamento auditado em transação;
- metadados administrativos de cancelamento expostos em “Minhas reservas” e check-in bloqueado;
- avisos internos públicos por período de visibilidade e banner na página inicial;
- auditoria das mutações administrativas de calendário, exceção e aviso;
- relatório mensal com origem, minutos operacionais por dia e reservas por estado;
- seeds regular e histórico coerentes com o calendário;
- ADR, OpenAPI, regras, arquitetura e diagramas sincronizados.

## Concluído na entrega do Modelo C

- reservas com `slot_count` consecutivo e usos imediatos com fim planejado em grade fixa;
- duração fixa de 15 minutos e tolerâncias fixas de três minutos fora de `BookingPolicy`;
- deadlines de check-in e saída e motivo `TIME_LIMIT_REACHED`;
- janela de check-in de três minutos antes a três minutos depois, sem deslocar o fim da reserva;
- conflitos por todo o intervalo planejado contra reservas, sessões e fechamento;
- troca validada até o fim planejado e bloqueada durante a tolerância;
- disponibilidade futura limitada por `planned_ends_at` e estado atual por `exit_deadline_at`;
- resposta `immediate_usage` resumida e opções de fim planejado no detalhe do computador;
- reconciliação oportunista e comando periódico que registra saídas automáticas e cancelamentos por check-in expirado;
- migração em três fases com bloqueio explícito de sessões legadas ativas;
- testes de constraints, APIs, deadlines, backfill e corridas entre reserva, entrada e troca;
- protótipo, ADR, documentação e diagramas sincronizados.

## Concluído na normalização do domínio e indisponibilidade operacional

- perfis persistidos e simulados usam `ROOM_MONITOR` e referência `demo-room-monitor`;
- reservas possuem somente `CONFIRMED`, `CANCELLED` e `USED`;
- check-in expirado e mudança de calendário usam cancelamento administrativo comum;
- `CalendarException` possui somente `CLOSED` e `SPECIAL_HOURS`;
- `BookingPolicy` é versionada por vigência e cada reserva referencia a versão aplicada;
- `AVAILABLE -> MAINTENANCE/INACTIVE` transfere ou encerra sessão ativa e realoca ou cancela reservas atomicamente;
- resposta do endpoint de estado descreve o impacto e as corridas usam locks determinísticos;
- Monitor continua sem acesso ao relatório mensal.

## Concluído na entrega do frontend do Usuário da Sala

- app de apresentação `web`, sem models, com páginas completas e partials HTMX;
- seletor visual dos quatro perfis e identidade fictícia obrigatória para o Usuário da Sala;
- proteção de todas as rotas `/sala/` pelo perfil armazenado na sessão;
- interface mobile-first de computadores, agenda, sessão e problemas;
- disponibilidade real de hoje e amanhã, busca server-side e avisos operacionais;
- reservas futuras para hoje e amanhã com opções consecutivas calculadas no servidor;
- entrada imediata, check-in, troca de computador, saída e histórico de alocações;
- ocorrências próprias com vínculo automático à alocação ativa correspondente;
- dialogs responsivos, mensagens acessíveis e reapresentação de estado após conflitos;
- navegação por clique, teclado e swipe, com limites, predominância horizontal e movimento reduzido;
- build local versionado com Tailwind CSS 4, HTMX e Alpine.js;
- E2E sobre Django e PostgreSQL reais em viewports mobile com toque e desktop.

## Concluído na entrega dos frontends operacionais e gerenciais

- área responsiva do Monitor da Sala em `/monitor/`, protegida para perfis operacionais;
- painel de sessões ativas, funcionamento vigente e resumo da operação;
- consulta de computadores e alteração de estado operacional com resultado explícito de realocações, encerramentos e cancelamentos;
- registro, pesquisa e transição de ocorrências conforme o ciclo de vida do domínio;
- histórico de sessões e correção restrita de horários com justificativa auditada;
- área responsiva do Supervisor da Biblioteca em `/supervisor/`, protegida para perfis gerenciais;
- cadastro e edição do inventário de computadores e acesso herdado ao painel operacional;
- criação, edição e substituição versionada de turnos analíticos sem alterar o calendário operacional;
- gestão de calendários regulares e temporários com prévia vinculada à proposta e confirmação explícita de cancelamentos;
- gestão de exceções pontuais com prévia de impacto, avisos internos e políticas de reserva;
- configuração auditada da apresentação de relatórios e visualização do relatório mensal disponível;
- busca server-side, páginas completas sem HTMX e shell compartilhado mobile-first com sidebar no desktop;
- testes Django dos fluxos críticos e E2E real ampliado para Monitor e Supervisor.
- paginação fixa de 25 itens nas listagens extensas da API e das interfaces, com busca da Agenda e do Histórico executada no banco;
- constraints de coerência entre estados e metadados de cancelamento, saída e encerramento, precedidas por migration de validação explícita do legado;
- serviços de configuração e views do Supervisor expostos em módulos coesos, preservando imports públicos, URLs e regras transacionais.

## Não implementado

- demais projeções e exportadores de relatórios;
- interface funcional própria do Administrador;
- autenticação real.

## Próxima fatia recomendada

Implementar o relatório diário e reutilizar calendário e projeção mensal nas exportações futuras.
