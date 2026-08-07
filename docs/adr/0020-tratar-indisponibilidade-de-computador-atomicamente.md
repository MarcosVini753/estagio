# ADR 0020: Tratar indisponibilidade operacional de computador atomicamente

## Status

Aceita.

## Contexto

O estado `MAINTENANCE` ou `INACTIVE` podia ser gravado enquanto o computador mantinha alocação ativa e reservas confirmadas. Como o estado operacional precede `OCCUPIED` e `RESERVED` na disponibilidade, a interface ocultava a sessão e preservava compromissos que o computador não poderia atender.

O domínio já representa a continuidade de uma sessão por múltiplas `ComputerAllocation` e valida computadores por intervalos completos. Criar um segundo mecanismo de uso duplicaria essas regras.

## Decisão

Uma transição de `AVAILABLE` para `MAINTENANCE` ou `INACTIVE` será orquestrada em `operations/services/computer_state.py` dentro de uma única transação.

Depois de reconciliar deadlines, o serviço bloqueia computadores em ordem de chave primária, a alocação e sessão ativas e as reservas confirmadas ainda utilizáveis. Se houver sessão ativa, procura computador `AVAILABLE` sem conflito em `[now, planned_ends_at)`. Encontrando destino, encerra a alocação com `COMPUTER_UNAVAILABLE` e cria a seguinte na mesma sessão; sem destino, encerra sessão e alocação com o mesmo motivo. `SWITCH` permanece reservado à troca normal.

Cada reserva é tratada independentemente. Um destino deve permanecer livre durante todo o intervalo reservado. A reserva preserva identidade, horários, deadlines e política; apenas `computer_id` muda. Sem destino, ela passa a `CANCELLED` com autor, instante e motivo.

Somente após reconciliar os impactos o serviço altera o estado, registra `ComputerOperationalStateChange` e cria auditoria. Qualquer falha reverte tudo. Transições entre estados já indisponíveis e retorno a `AVAILABLE` não modificam sessões ou reservas.

## Consequências

- um computador indisponível não permanece associado a alocação ativa após uma operação válida;
- sessões mantêm identidade e histórico durante transferência;
- reservas continuam atendidas quando há alternativa;
- a resposta da API descreve transferências, encerramentos, realocações e cancelamentos;
- bloquear todos os computadores serializa mudanças de estado, escolha simples e deliberada para evitar destinos duplicados no tamanho atual da sala;
- constraints PostgreSQL continuam sendo a última barreira contra sobreposição.
