# Modelo de domínio

## Convenções

- identificadores internos preferencialmente UUID ou chave numérica, decisão final na implementação;
- todos os registros relevantes possuem `created_at` e `updated_at`;
- datas e horários são timezone-aware;
- estados usam `TextChoices`;
- regras críticas são reforçadas por constraints quando possível;
- nomes dos campos no código permanecem em inglês.

## `Computer`

```text
id
code
asset_number, opcional
description
operational_state
notes
created_at
updated_at
```

`operational_state`:

- `AVAILABLE`;
- `MAINTENANCE`;
- `INACTIVE`.

Não criar campos `occupied`, `reserved`, `status_today` ou `status_tomorrow`.

## `ComputerOperationalStateChange`

```text
id
computer_id
previous_state
new_state
actor_profile
reason
changed_at
```

Mantém histórico para auditoria e cálculo de disponibilidade operacional histórica.

## `Shift`

```text
id
name
start_time
end_time
display_order
valid_from
valid_until
is_active
```

A validade temporal impede que uma alteração de turno reclassifique silenciosamente relatórios antigos.

## `CalendarException`

```text
id
date
exception_type
opens_at, opcional
closes_at, opcional
description
```

Tipos sugeridos:

- `CLOSED`;
- `SPECIAL_HOURS`;
- `OPTIONAL_HOLIDAY`.

## `BookingPolicy`

```text
id
slot_duration_minutes
check_in_tolerance_minutes
cancellation_limit_minutes
max_future_reservations_per_user
is_active
valid_from
```

A regra de reserva apenas para amanhã continua no domínio e não deve depender somente desse modelo.

## `Reservation`

```text
id
user_reference
computer_id
starts_at
ends_at
status
created_by_profile
cancelled_by_profile, opcional
cancelled_at, opcional
cancellation_reason, opcional
created_at
updated_at
```

Estados sugeridos:

- `CONFIRMED`;
- `CANCELLED`;
- `USED`;
- `NO_SHOW`;
- `INVALIDATED`.

No MVP sem autenticação, `user_reference` representa uma pessoa fictícia ou identificador de demonstração, não uma identidade validada.

## `UseSession`

```text
id
user_reference
reservation_id, opcional
started_at
ended_at, opcional
status
start_shift_id, opcional
entry_recorded_by_profile
exit_recorded_by_profile, opcional
created_at
updated_at
```

Estados:

- `ACTIVE`;
- `FINISHED`;
- `CANCELLED`.

## `ComputerAllocation`

```text
id
session_id
computer_id
sequence
started_at
ended_at, opcional
end_reason, opcional
switch_reason, opcional
created_at
updated_at
```

Uma sessão possui uma ou mais alocações. Apenas uma alocação da sessão pode permanecer ativa.

## `Occurrence`

```text
id
reported_by_reference
computer_id, opcional
session_id, opcional
allocation_id, opcional
description
status
resolved_by_profile, opcional
resolution_notes, opcional
created_at
resolved_at, opcional
updated_at
```

Estados:

- `OPEN`;
- `IN_REVIEW`;
- `RESOLVED`;
- `CANCELLED`.

## `AuditEvent`

```text
id
actor_profile
action
entity_type
entity_id
old_values
new_values
reason
created_at
```

## Restrições recomendadas

- uma sessão ativa por `user_reference`;
- uma alocação ativa por computador;
- uma alocação ativa por sessão;
- `starts_at < ends_at` quando houver término;
- reservas válidas não podem se sobrepor no mesmo computador;
- reservas do mesmo usuário não podem se sobrepor;
- `sequence` é única dentro da sessão;
- estado operacional aceita apenas os três valores definidos.

## Relacionamentos principais

```text
Reservation 0..1 ─── 1 UseSession
UseSession 1 ─────── * ComputerAllocation
Computer 1 ───────── * ComputerAllocation
Computer 1 ───────── * Reservation
Computer 1 ───────── * Occurrence
Computer 1 ───────── * ComputerOperationalStateChange
Shift 0..1 ───────── * UseSession
```
