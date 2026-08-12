# Auditoria e testes

## Auditoria

Mesmo com autorização simulada, ações sensíveis devem registrar o perfil selecionado, a operação, o alvo, valores anteriores e novos, justificativa e horário.

Eventos mínimos:

- alteração de estado operacional;
- correção de sessão ou alocação;
- cancelamento administrativo;
- realocação automática de reserva;
- encerramento de sessão por computador indisponível;
- alteração de turno;
- alteração de política de reserva;
- alteração de parâmetros de relatório;
- ações futuras de contas e permissões.

O registro de auditoria não substitui autenticação. No MVP, ele demonstra rastreabilidade funcional, mas não comprova a identidade real do autor.

## Estratégia de testes

### Testes unitários

Cobrir:

- cálculo de hoje e amanhã;
- rejeição de datas fora da janela;
- rejeição de horários passados;
- precedência do estado efetivo;
- cálculo de slots;
- cálculo do intervalo por `slot_count` e do máximo para uso imediato;
- separação entre fim planejado, prazo de saída e término real;
- classificação de turnos;
- projeções de relatórios.

### Testes de serviços

Cobrir:

- criação de reserva;
- conflito de reserva;
- intervalos adjacentes e intervalos que atravessam reserva ou fechamento;
- entrada imediata;
- entrada com reserva;
- check-in sem antecipação, em `+3:00` e após o prazo;
- sessão duplicada;
- alocação duplicada;
- troca de computador;
- troca pelo intervalo planejado restante e rejeição durante tolerância;
- saída antecipada, no prazo e expiração lógica;
- reconciliação de cancelamento por check-in expirado e `TIME_LIMIT_REACHED`;
- correção auditada;
- alteração de estado operacional com transferência/encerramento de sessão e realocação/cancelamento de reservas;
- substituição transacional de turno e preservação da versão usada por sessão.

### Testes de API

Cobrir:

- contrato de respostas;
- códigos de erro;
- filtros e paginação;
- acesso por perfil simulado;
- serialização temporal;
- rotas e contratos documentados no OpenAPI.

### Testes de integração

Usar PostgreSQL para validar:

- constraints condicionais;
- bloqueios transacionais;
- concorrência de reservas;
- concorrência entre reserva e entrada imediata;
- concorrência entre reserva e troca;
- concorrência entre manutenção e reserva ou entrada;
- duas indisponibilizações disputando o mesmo destino;
- consultas agregadas.

### Testes de interface

Cobrir os fluxos principais do protótipo:

1. escolher perfil;
2. consultar hoje;
3. iniciar e encerrar sessão;
4. trocar de computador;
5. reservar amanhã;
6. selecionar vários slots consecutivos e conferir fim planejado e prazo;
7. registrar ocorrência;
8. acessar e operar o painel do Monitor;
9. gerenciar inventário, funcionamento e avisos pelo Supervisor;
10. pré-visualizar o impacto de calendário antes da confirmação;
11. acessar o relatório mensal com parâmetros gerenciais.

## Invariantes que devem falhar no banco ou serviço

- mais de uma sessão ativa por usuário;
- mais de uma alocação ativa por computador;
- mais de uma alocação ativa na mesma sessão;
- reserva sobreposta válida;
- reserva ou sessão planejada fora de uma janela operacional;
- entrada anterior ao início planejado;
- sessão sem fim planejado ou prazo de saída;
- intervalo com término anterior ao início;
- uso imediato em data diferente de hoje;

## Dados de teste

Criar factories para:

- perfis de demonstração;
- computadores em cada estado operacional;
- turnos;
- reservas;
- sessões e alocações;
- deadlines e reconciliação operacional;
- ocorrências.

Nenhum teste ou fixture inicial deve conter dados pessoais reais.

## Critério de qualidade

Toda correção de bug deve adicionar teste de regressão. Mudanças de regra funcional devem atualizar documentação e testes no mesmo pull request.
