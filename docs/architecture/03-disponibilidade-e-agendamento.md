# Disponibilidade e agendamento

## Objetivo

Centralizar a regra que determina se um computador pode ser consultado, utilizado imediatamente ou reservado.

## Entradas da consulta

- computador;
- data;
- instante ou intervalo;
- perfil de teste atual;
- usuário fictício selecionado, quando necessário.

## Janela temporal

```text
hoje    -> consulta e uso imediato ou reserva antecipada
amanhã  -> consulta e reserva antecipada
outras datas -> rejeitadas
```

Para hoje, intervalos cujo início já passou são indisponíveis para novo uso.

## Estado efetivo

Precedência:

```text
INACTIVE
MAINTENANCE
OCCUPIED
RESERVED
AVAILABLE
```

Algoritmo conceitual:

```python
if computer.operational_state == "INACTIVE":
    return "INACTIVE"
if computer.operational_state == "MAINTENANCE":
    return "MAINTENANCE"
if has_overlapping_active_allocation(computer, interval):
    return "OCCUPIED"
if has_overlapping_valid_reservation(computer, interval):
    return "RESERVED"
return "AVAILABLE"
```

Uma reserva pertencente ao usuário atual pode ser indicada adicionalmente por `reserved_by_current_user`, mas o estado efetivo continua `RESERVED`.

## Slots

Os slots são derivados de:

- calendário operacional efetivo;
- duração fixa de 15 minutos;
- exceções de calendário;
- reservas válidas;
- alocações existentes;
- estado operacional do computador;
- horário atual quando a data é hoje.

Não persistir todos os slots como registros se eles puderem ser calculados. Persistir somente eventos reais: reservas, sessões e alocações.

Reservas recebem `slot_count` e combinam slots consecutivos em um único intervalo semiaberto `[início, fim)`. O início é alinhado a cada janela operacional; o intervalo inteiro deve permanecer dentro da mesma janela.

## Resolução do funcionamento

O resolvedor compartilhado em `configuration/calendar.py` aplica:

```text
CalendarException da data
  > OperatingSchedule TEMPORARY
  > OperatingSchedule REGULAR
  > OPERATING_SCHEDULE_REQUIRED
```

Domingo é um dia regular explicitamente fechado, não ausência de configuração. O algoritmo de disponibilidade começa por:

```python
operating_day = resolve_operating_day(target_date)

if operating_day.is_closed:
    return no_slots(reason=operating_day.reason)

slots = generate_slots(operating_day.windows)
```

De segunda a sexta o horário regular inicial é 07h15–21h; sábado é 07h15–13h. `Shift` não participa desta resolução.

## Uso imediato

Operação transacional:

1. receber computador e `slot_count >= 1`;
2. reconciliar prazos vencidos no computador, nas sessões ativas do usuário e em suas reservas confirmadas já vencidas;
3. calcular `[agora, agora + slot_count × 15 minutos)`;
4. validar que todo o intervalo cabe na janela operacional;
5. bloquear referência de usuário e computador;
6. verificar reservas do computador e do próprio usuário durante todo o intervalo;
7. verificar sessões planejadas conflitantes;
8. criar `UseSession` com fim planejado e prazo de saída três minutos depois;
9. criar a primeira `ComputerAllocation`.

A resposta de disponibilidade inclui `immediate_usage` com `can_start_now`, `max_slot_count`, `max_planned_ends_at` e `limited_by`. O limite pode ser próxima reserva, reserva do usuário, fechamento, alocação ativa ou estado operacional indisponível.

## Reserva antecipada

Operação transacional:

1. validar que a data é hoje ou amanhã e o início ainda é futuro;
2. calcular o fim por `slot_count` e validar alinhamento de 15 minutos;
3. validar o intervalo inteiro em uma única janela operacional;
4. bloquear referência de usuário e computador;
5. verificar reservas e sessões planejadas do computador e do usuário;
6. criar `Reservation` com deadlines de três minutos e estado `CONFIRMED`.

## Troca de computador

Operação transacional:

1. validar sessão ativa;
2. validar computador de destino diferente do atual;
3. rejeitar a operação quando o fim planejado já chegou;
4. bloquear referência de usuário, alocação atual e computadores;
5. validar o destino em `[agora, planned_ends_at)` contra reservas e sessões planejadas;
6. encerrar alocação atual;
7. criar nova alocação com sequência seguinte;
8. manter a mesma sessão e seus prazos.

## Saída

Operação transacional:

1. localizar sessão ativa;
2. permitir saída real até `exit_deadline_at`, inclusive;
3. encerrar alocação atual e sessão com o horário real;
4. produzir evento de auditoria se a saída for administrativa.

Quando `now >= exit_deadline_at`, a reconciliação encerra logicamente sessão e alocação em `exit_deadline_at`, usando `TIME_LIMIT_REACHED`. Reserva permanece `CONFIRMED` até `now > check_in_deadline_at`, quando passa a `NO_SHOW`. O comando `reconcile_operational_deadlines` executa ambas as rotinas, deve ser agendado externamente a cada minuto e as entradas/trocas reconciliam oportunisticamente os computadores envolvidos. Na entrada, isso inclui computadores com sessão ativa ou reserva vencida do próprio usuário.

## Planejado, atual e histórico

- conflitos futuros usam `planned_ends_at` e ignoram os três minutos de tolerância;
- o estado atual usa `exit_deadline_at` enquanto a alocação não foi encerrada;
- o histórico usa `ComputerAllocation.started_at` e `ended_at` reais;
- por isso uma sessão planejada até 09h libera os slots a partir de 09h, embora possa aparecer ocupada no instante atual até 09h03.

## Mudança de calendário e reservas

Antes de salvar uma redução de horário, o preview consulta reservas confirmadas dentro da vigência e identifica intervalos fora das novas janelas. Na confirmação, calendário, reservas e eventual aviso são gravados em uma transação:

1. bloquear calendários do mesmo tipo e reservas confirmadas do período;
2. salvar a configuração nova ou sua versão substituta;
3. recalcular o calendário efetivo, preservando exceções e precedência;
4. rejeitar com `SCHEDULE_CHANGE_AFFECTS_RESERVATIONS` se faltou confirmação;
5. marcar conflitos como `INVALIDATED`, com perfil, horário e motivo;
6. registrar auditoria do calendário e de cada reserva;
7. criar aviso vinculado, quando solicitado;
8. confirmar a transação.

## Concorrência

Usar `transaction.atomic()`, advisory lock por referência de usuário e bloqueios pessimistas com `select_for_update()` nas operações que disputam computadores. Reserva, entrada imediata e troca são serializadas pelos mesmos alvos. Constraints de banco funcionam como última barreira contra duplicidade.

## Erros de domínio sugeridos

- `DATE_OUTSIDE_ALLOWED_WINDOW`;
- `PAST_TIME_NOT_ALLOWED`;
- `COMPUTER_NOT_OPERATIONAL`;
- `COMPUTER_NOT_AVAILABLE`;
- `USER_ALREADY_HAS_ACTIVE_SESSION`;
- `USER_HAS_CONFLICTING_RESERVATION`;
- `RESERVATION_CONFLICT`;
- `NO_ACTIVE_SESSION`;
- `SAME_COMPUTER_SWITCH`.
