# Auditoria e testes

## Auditoria

Mesmo com autorização simulada, ações sensíveis devem registrar o perfil selecionado, a operação, o alvo, valores anteriores e novos, justificativa e horário.

Eventos mínimos:

- alteração de estado operacional;
- correção de sessão ou alocação;
- cancelamento administrativo;
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
- classificação de turnos;
- projeções de relatórios.

### Testes de serviços

Cobrir:

- criação de reserva;
- conflito de reserva;
- entrada imediata;
- entrada com reserva;
- sessão duplicada;
- alocação duplicada;
- troca de computador;
- saída;
- correção auditada;
- alteração de estado operacional.

### Testes de API

Cobrir:

- contrato de respostas;
- códigos de erro;
- filtros e paginação;
- acesso por perfil simulado;
- serialização temporal;
- endpoints versionados.

### Testes de integração

Usar PostgreSQL para validar:

- constraints condicionais;
- bloqueios transacionais;
- concorrência de reservas;
- concorrência de entrada e troca;
- consultas agregadas.

### Testes de interface

Cobrir os fluxos principais do protótipo:

1. escolher perfil;
2. consultar hoje;
3. iniciar e encerrar sessão;
4. trocar de computador;
5. reservar amanhã;
6. registrar ocorrência;
7. acessar painel operacional e relatórios.

## Invariantes que devem falhar no banco ou serviço

- mais de uma sessão ativa por usuário;
- mais de uma alocação ativa por computador;
- mais de uma alocação ativa na mesma sessão;
- reserva sobreposta válida;
- intervalo com término anterior ao início;
- uso imediato em data diferente de hoje;

## Dados de teste

Criar factories para:

- perfis de demonstração;
- computadores em cada estado operacional;
- turnos;
- reservas;
- sessões e alocações;
- ocorrências.

Nenhum teste ou fixture inicial deve conter dados pessoais reais.

## Critério de qualidade

Toda correção de bug deve adicionar teste de regressão. Mudanças de regra funcional devem atualizar documentação e testes no mesmo pull request.
