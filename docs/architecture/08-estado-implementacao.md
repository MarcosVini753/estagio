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
- geração de slots a partir de turnos, exceções e duração configurada;
- consulta de disponibilidade somente para hoje ou amanhã;
- descarte de slots iniciados no passado;
- cálculo dos estados efetivos `OCCUPIED` e `RESERVED`;
- precedência de `INACTIVE` e `MAINTENANCE`;
- identificação de reserva pertencente ao usuário fictício atual;
- seed idempotente para o ambiente de demonstração;
- testes de API e regras de disponibilidade.
- criação, listagem e cancelamento transacionais de reservas;
- constraints PostgreSQL contra sobreposição de reservas confirmadas.

## Concluído na Pré-Etapa 4

- contexto fictício ampliado para Usuário da Sala, com referência, vínculo e unidade institucional;
- snapshots de vínculo e unidade em reservas e sessões de uso;
- compatibilidade histórica para registros sem contexto, agrupáveis como `NOT_INFORMED`.
- versionamento futuro de turnos, com substituição auditada e preservação dos turnos já usados.

## Não implementado

- entrada, saída e troca por serviços transacionais;
- tratamento de ocorrências via API;
- selectors e exportadores de relatórios;
- migração do protótipo para Django Templates;
- autenticação real.

## Próxima fatia recomendada

Concluir a Etapa 3.5 com entrada, sessão ativa, troca, saída, ocorrências, correções auditadas e dados históricos de demonstração antes de iniciar relatórios.
