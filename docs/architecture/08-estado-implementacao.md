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

## Concluído na etapa 3

- endpoints de computadores;
- criação e edição de computadores pelo Supervisor ou Administrador;
- alteração de estado operacional pelo Estagiário, Supervisor ou Administrador;
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

## Não implementado

- criação e cancelamento de reservas;
- constraint PostgreSQL contra reservas sobrepostas;
- entrada, saída e troca por serviços transacionais;
- tratamento de ocorrências via API;
- selectors e exportadores de relatórios;
- migração do protótipo para Django Templates;
- autenticação real.

## Próxima fatia recomendada

Implementar reservas, entrada, sessão ativa, troca de computador e saída. As operações devem usar transações, bloqueios e as constraints existentes, reutilizando o serviço de disponibilidade da etapa 3.
