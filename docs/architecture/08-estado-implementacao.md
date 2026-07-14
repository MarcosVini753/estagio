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
- OpenAPI, Swagger UI e ReDoc;
- formato padronizado de erro;
- testes iniciais;
- Ruff e GitHub Actions.

## Não implementado

- cálculo de disponibilidade efetiva;
- geração de slots;
- criação/cancelamento de reservas;
- prevenção concorrente de reservas sobrepostas;
- entrada, saída e troca por serviços transacionais;
- endpoints de computadores, configurações e ocorrências;
- selectors e exportadores de relatórios;
- migração do protótipo completo;
- autenticação real.

## Próxima fatia recomendada

Implementar computadores, turnos e disponibilidade somente para leitura, incluindo cálculo de `AVAILABLE`, `MAINTENANCE`, `INACTIVE`, `OCCUPIED` e `RESERVED`, com testes de hoje, amanhã e timezone de Rio Branco.
