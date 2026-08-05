# Modelo de domínio

## Convenções implementadas

- chaves primárias `BigAutoField`;
- campos em inglês;
- `created_at` e `updated_at` nas entidades mutáveis relevantes;
- datas timezone-aware em `America/Rio_Branco`;
- estados com `TextChoices`;
- PostgreSQL como banco-alvo;
- referências de usuário fictícias no MVP sem autenticação.

## Configuração

### `Shift`

`series_key`, `name`, `start_time`, `end_time`, `display_order`, `valid_from`, `valid_until`, `is_active`.

Constraints: início anterior ao fim e validade final não anterior à inicial.

Turnos usados por `UseSession.start_shift` preservam seus horários e vigência. A substituição cria uma nova versão futura, mantendo a referência histórica da sessão na versão anterior.
Versões do mesmo turno lógico compartilham `series_key`, usado para agrupamento analítico.

### `CalendarException`

`date`, `exception_type`, `opens_at`, `closes_at`, `description`.

Tipos: `CLOSED`, `SPECIAL_HOURS`, `OPTIONAL_HOLIDAY`.

### `BookingPolicy`

`slot_duration_minutes`, `check_in_tolerance_minutes`, `cancellation_limit_minutes`, `max_future_reservations_per_user`, `is_active`, `valid_from`.

### `ReportConfiguration`

`default_format`, `group_by_shift`, `include_occurrences`, `is_active`.

## Computadores

### `Computer`

`code`, `asset_number`, `description`, `operational_state`, `notes`.

Estado persistido: `AVAILABLE`, `MAINTENANCE`, `INACTIVE`. Não criar campos de ocupado ou reservado.

### `ComputerOperationalStateChange`

`computer`, `previous_state`, `new_state`, `actor_profile`, `reason`, `changed_at`.

## Operações

### `Reservation`

`user_reference`, snapshots de `affiliation_type` e `institutional_unit`, `computer`, `starts_at`, `ends_at`, `status`, perfis de criação/cancelamento e dados de cancelamento.

Estados: `CONFIRMED`, `CANCELLED`, `USED`, `NO_SHOW`, `INVALIDATED`.

Constraints PostgreSQL impedem sobreposição de reservas confirmadas por computador e por usuário com intervalos `[)`. O serviço bloqueia computador e referência de usuário para validar slots, limite e disponibilidade antes da criação.

### `UseSession`

`user_reference`, snapshots de `affiliation_type` e `institutional_unit`, `reservation`, `started_at`, `ended_at`, `status`, `start_shift` e perfis de entrada/saída.

Os snapshots preservam vínculo e unidade no momento da reserva ou entrada. Registros legados usam `NOT_INFORMED` e unidade vazia.

Estados: `ACTIVE`, `FINISHED`, `CANCELLED`.

Constraint: uma sessão ativa por referência de usuário.

### `ComputerAllocation`

`session`, `computer`, `sequence`, `started_at`, `ended_at`, `end_reason`, `switch_reason`.

Constraints: sequência única; uma alocação ativa por computador; uma alocação ativa por sessão; término não anterior ao início; intervalos históricos do mesmo computador sem sobreposição.

## Ocorrências

### `Occurrence`

`reported_by_reference`, vínculos opcionais com computador, sessão e alocação, `description`, `status`, resolução e horários.

Estados: `OPEN`, `IN_REVIEW`, `RESOLVED`, `CANCELLED`.

## Auditoria

### `AuditEvent`

`actor_profile`, `action`, `entity_type`, `entity_id`, `old_values`, `new_values`, `reason`, `created_at`.

## Relatórios

O app `reports` não possui modelo agregado. Relatórios serão selectors, projeções e exportadores sobre os registros acima.
