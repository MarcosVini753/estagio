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
- duração configurada;
- exceções de calendário;
- reservas válidas;
- alocações existentes;
- estado operacional do computador;
- horário atual quando a data é hoje.

Não persistir todos os slots como registros se eles puderem ser calculados. Persistir somente eventos reais: reservas, sessões e alocações.

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

1. validar que a data é hoje;
2. validar que o horário não passou;
3. bloquear o computador durante a transação;
4. recalcular disponibilidade;
5. garantir que usuário e computador não possuem sessão/alocação ativa conflitante;
6. criar `UseSession`;
7. criar primeira `ComputerAllocation`;
8. retornar sessão ativa.

## Reserva antecipada

Operação transacional:

1. validar que a data é hoje ou amanhã;
2. validar intervalo e política;
3. bloquear registros necessários;
4. recalcular disponibilidade;
5. verificar conflitos do computador e do usuário;
6. criar `Reservation` com estado `CONFIRMED`.

## Troca de computador

Operação transacional:

1. validar sessão ativa;
2. validar computador de destino diferente do atual;
3. bloquear alocação atual e computador de destino;
4. recalcular disponibilidade do destino;
5. encerrar alocação atual;
6. criar nova alocação com sequência seguinte;
7. manter a mesma sessão.

## Saída

Operação transacional:

1. localizar sessão ativa;
2. encerrar alocação atual;
3. encerrar sessão;
4. marcar reserva relacionada como `USED`, quando aplicável;
5. produzir evento de auditoria se a saída for administrativa.

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

Usar `transaction.atomic()` e bloqueios pessimistas com `select_for_update()` nas operações que disputam computadores. Constraints de banco devem funcionar como última barreira contra duplicidade.

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
