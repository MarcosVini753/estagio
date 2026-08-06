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
- geração de slots a partir do calendário efetivo, exceções e duração configurada;
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
- preview de reservas afetadas, confirmação e invalidação auditada em transação;
- metadados de invalidação expostos em “Minhas reservas” e check-in bloqueado;
- avisos internos públicos por período de visibilidade e banner na página inicial;
- auditoria das mutações administrativas de calendário, exceção e aviso;
- relatório mensal com origem, minutos operacionais por dia e reservas por estado;
- seeds regular e histórico coerentes com o calendário;
- ADR, OpenAPI, regras, arquitetura e diagramas sincronizados.

## Não implementado

- demais projeções e exportadores de relatórios;
- migração das demais telas do protótipo para Django Templates;
- autenticação real.

## Próxima fatia recomendada

Implementar o relatório diário e reutilizar calendário e projeção mensal nas exportações futuras.
