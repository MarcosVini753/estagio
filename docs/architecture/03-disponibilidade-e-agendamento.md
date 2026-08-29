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

1. receber computador e `planned_ends_at`;
2. reconciliar prazos vencidos no computador, nas sessões ativas do usuário e em suas reservas confirmadas já vencidas;
3. validar que o fim pertence à grade global `07:15 + N × 15 minutos`, é posterior a `agora` e forma `[agora, fim)` dentro da mesma janela operacional;
4. validar que todo o intervalo cabe na janela operacional;
5. bloquear referência de usuário e computador;
6. verificar reservas do computador e do próprio usuário durante todo o intervalo;
7. verificar sessões planejadas conflitantes;
8. criar `UseSession` com fim planejado e prazo de saída três minutos depois;
9. criar a primeira `ComputerAllocation`.

A resposta resumida de disponibilidade inclui `immediate_usage` com `can_start_now`, `max_planned_ends_at` e `limited_by`. O detalhe de um computador inclui adicionalmente `planned_end_options`, calculado no servidor. O limite pode ser próxima reserva, reserva do usuário, fechamento, alocação ativa ou estado operacional indisponível.

Quando uma reserva ou o fechamento ocorre fora da grade global, as opções terminam na última marca anterior. Assim, um fechamento às 13h10 oferece 13h00 como último fim planejado; o limite exato só é selecionável quando também pertence à grade.

## Reserva antecipada

Operação transacional:

1. validar que a data é hoje ou amanhã e o início ainda é futuro;
2. calcular o fim por `slot_count` e validar alinhamento de 15 minutos;
3. validar o intervalo inteiro em uma única janela operacional;
4. bloquear referência de usuário e computador;
5. verificar reservas e sessões planejadas do computador e do usuário;
6. vincular a versão de `BookingPolicy` vigente e criar `Reservation` com deadlines de três minutos e estado `CONFIRMED`.

## Entrada com reserva

A entrada vinculada a uma reserva confirmada é aceita no intervalo fechado `[starts_at - 3 minutos, check_in_deadline_at]`, desde que a sala e o computador estejam aptos ao uso. O serviço copia o intervalo planejado e o prazo de saída da reserva, registra o horário real de entrada e não desloca `planned_starts_at`, `planned_ends_at` nem `exit_deadline_at`.

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

Quando `now >= exit_deadline_at`, a reconciliação registra automaticamente a saída e encerra sessão e alocação em `exit_deadline_at`, usando `TIME_LIMIT_REACHED`. Reserva permanece `CONFIRMED` até `now > check_in_deadline_at`, quando passa a `CANCELLED` com autor sistêmico e motivo explícito. O comando `reconcile_operational_deadlines` executa ambas as rotinas, deve ser agendado externamente a cada minuto e as entradas/trocas reconciliam oportunisticamente os computadores envolvidos.

## Planejado, atual e histórico

- conflitos futuros usam o intervalo planejado e ignoram os três minutos de tolerância de entrada e saída;
- o estado atual usa `exit_deadline_at` enquanto a alocação não foi encerrada;
- o histórico usa `ComputerAllocation.started_at` e `ended_at` reais;
- por isso uma sessão planejada até 09h libera os slots a partir de 09h, embora possa aparecer ocupada no instante atual até 09h03.

## Mudança de calendário e reservas

Antes de salvar uma redução de horário, o preview consulta reservas confirmadas dentro da vigência e identifica intervalos fora das novas janelas. Na confirmação, calendário, reservas e eventual aviso são gravados em uma transação:

1. bloquear calendários do mesmo tipo e reservas confirmadas do período;
2. salvar a configuração nova ou sua versão substituta;
3. recalcular o calendário efetivo, preservando exceções e precedência;
4. rejeitar com `SCHEDULE_CHANGE_AFFECTS_RESERVATIONS` se faltou confirmação;
5. cancelar administrativamente os conflitos, com perfil, horário e motivo;
6. registrar auditoria do calendário e de cada reserva;
7. criar aviso vinculado, quando solicitado;
8. confirmar a transação.

## Indisponibilidade operacional do computador

Ao mudar um computador de `AVAILABLE` para `MAINTENANCE` ou `INACTIVE`, `operations/services/computer_state.py` reconcilia prazos, bloqueia computadores, sessão, alocação e reservas em ordem determinística e então:

1. transfere a sessão ativa para um destino livre em `[now, planned_ends_at)` ou a encerra com `COMPUTER_UNAVAILABLE`;
2. realoca cada reserva confirmada para um computador livre durante seu intervalo ou a cancela administrativamente;
3. altera o estado do computador e registra histórico e auditoria;
4. confirma tudo em uma única transação.

Transições que não saem de `AVAILABLE`, como `MAINTENANCE -> INACTIVE` ou `MAINTENANCE -> AVAILABLE`, apenas alteram o estado.

## Concorrência

Usar `transaction.atomic()`, advisory lock por referência de usuário e bloqueios pessimistas com `select_for_update()` nas operações que disputam computadores. A indisponibilização bloqueia os computadores por chave primária para que duas operações não escolham o mesmo destino. Constraints de banco funcionam como última barreira contra duplicidade.

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
