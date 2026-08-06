# API

## Endereçamento

A API começa em `/api/` e não inclui versão nas URLs. Mudanças incompatíveis exigem migração planejada e nova decisão arquitetural, sem manter infraestrutura de versões paralelas enquanto não existir essa necessidade.

## Convenções

- JSON em `snake_case`;
- datas e horários em ISO 8601 com timezone;
- filtros por query string;
- erros com `code`, `detail` e `fields`;
- OpenAPI gerado com `drf-spectacular`;
- operações de domínio expostas como actions explícitas;
- endpoints protegidos pelo perfil de demonstração armazenado na sessão.

## Endpoints implementados

> Salvo indicação contrária, todo endpoint acessível ao Monitor da Sala também é acessível ao Supervisor da Biblioteca.

### Sistema e demonstração

```text
GET  /api/health/
GET  /api/demo/context/
POST /api/demo/select-profile/
```

A seleção de perfil simula autorização e não autentica uma identidade real.

`POST /api/demo/select-profile/` exige `user_reference`, `affiliation_type` e `institutional_unit` para `ROOM_USER`. `GET /api/demo/context/` devolve os valores selecionados; perfis operacionais devolvem apenas a referência fictícia fixa.

### Computadores

```text
GET   /api/computers/
POST  /api/computers/
GET   /api/computers/{id}/
PATCH /api/computers/{id}/
PATCH /api/computers/{id}/operational-state/
```

Leitura é permitida para qualquer perfil selecionado. Cadastro e edição são permitidos ao Supervisor e Administrador. A alteração de estado operacional também é permitida ao Monitor da Sala e sempre registra histórico.

O PATCH genérico não altera `operational_state`; a action específica deve ser usada para preservar auditoria e validações.

### Disponibilidade

```text
GET /api/computers/availability/?date=YYYY-MM-DD
GET /api/computers/{id}/slots/?date=YYYY-MM-DD
```

A data deve ser hoje ou amanhã. O primeiro endpoint devolve um resumo por computador:

```json
{
  "date": "2026-07-14",
  "is_today": true,
  "slot_duration_minutes": 15,
  "generated_at": "2026-07-14T09:30:00-05:00",
  "room": {
    "status": "OPEN",
    "source": "REGULAR_SCHEDULE",
    "reason": "",
    "operating_windows": [
      {"opens_at": "07:15:00", "closes_at": "21:00:00"}
    ],
    "active_notices": []
  },
  "computers": [
    {
      "id": 1,
      "code": "PC-01",
      "description": "Computador da Sala de Informática",
      "operational_state": "AVAILABLE",
      "effective_status_now": "AVAILABLE",
      "can_start_now": true,
      "immediate_usage": {
        "can_start_now": true,
        "max_slot_count": 2,
        "max_planned_ends_at": "2026-07-14T10:00:00-05:00",
        "limited_by": "NEXT_RESERVATION"
      },
      "available_slot_count": 4,
      "next_available_slot": {
        "starts_at": "2026-07-14T09:45:00-05:00",
        "ends_at": "2026-07-14T10:00:00-05:00"
      }
    }
  ]
}
```

`effective_status_now` é preenchido somente para hoje. Para amanhã, seu valor é `null`; a disponibilidade deve ser consultada pelos slots. `immediate_usage.limited_by` pode ser `NEXT_RESERVATION`, `USER_RESERVATION`, `ROOM_CLOSING`, `ACTIVE_ALLOCATION` ou `COMPUTER_UNAVAILABLE`. O máximo considera slots inteiros de 15 minutos a partir do instante real.

O endpoint de slots devolve intervalos derivados, não registros persistidos:

```json
{
  "computer": {
    "id": 1,
    "code": "PC-01",
    "operational_state": "AVAILABLE"
  },
  "date": "2026-07-15",
  "is_today": false,
  "slot_duration_minutes": 15,
  "immediate_usage": {
    "can_start_now": false,
    "max_slot_count": 0,
    "max_planned_ends_at": null,
    "limited_by": null
  },
  "room": {
    "status": "OPEN",
    "source": "REGULAR_SCHEDULE",
    "reason": "",
    "operating_windows": [
      {"opens_at": "07:15:00", "closes_at": "21:00:00"}
    ],
    "active_notices": []
  },
  "slots": [
    {
      "starts_at": "2026-07-15T07:15:00-05:00",
      "ends_at": "2026-07-15T07:30:00-05:00",
      "effective_status": "AVAILABLE",
      "reserved_by_current_user": false,
      "selectable": true
    }
  ]
}
```

Precedência do estado efetivo:

```text
INACTIVE > MAINTENANCE > OCCUPIED > RESERVED > AVAILABLE
```

O bloco `room` explica ausência de slots. Domingo, por exemplo, retorna `status=CLOSED`, `source=REGULAR_SCHEDULE`, motivo explícito e nenhuma janela. O calendário operacional, não `Shift`, define as janelas.

### Configuração operacional

```text
GET   /api/shifts/
POST  /api/shifts/
GET   /api/shifts/{id}/
PATCH /api/shifts/{id}/
POST  /api/shifts/{id}/replace/

GET  /api/operating-schedules/
POST /api/operating-schedules/
POST /api/operating-schedules/impact-preview/
GET   /api/operating-schedules/{id}/
PATCH /api/operating-schedules/{id}/
POST  /api/operating-schedules/{id}/replace/

GET   /api/calendar-exceptions/
POST  /api/calendar-exceptions/
GET   /api/calendar-exceptions/{id}/
PATCH /api/calendar-exceptions/{id}/

GET   /api/booking-policy/
PATCH /api/booking-policy/
```

Leitura é permitida para os perfis selecionados. Escrita é permitida ao Supervisor e Administrador. Cada turno expõe `series_key`; versões do mesmo turno lógico compartilham essa chave. Um turno já referenciado por sessão aceita apenas desativação via `PATCH`; `replace/` recebe `effective_from`, nome, horários e ordem, encerra a versão atual no dia anterior e retorna a nova versão com o mesmo `series_key`. A vigência deve começar após hoje, sem sobrepor outro turno ativo. Atualizar a política cria uma nova versão quando a versão vigente começou em data anterior ao dia atual. A política expõe somente limite de cancelamento e máximo de reservas futuras; duração de 15 minutos e tolerâncias de três minutos são regras fixas.

Calendários recebem exatamente sete dias. A API aceita `weekday` pelos nomes `MONDAY` a `SUNDAY`. Exemplo de criação temporária:

```json
{
  "name": "Recesso acadêmico 2026/2",
  "schedule_type": "TEMPORARY",
  "valid_from": "2026-12-21",
  "valid_until": "2027-01-31",
  "reason": "Funcionamento durante o recesso.",
  "days": [
    {
      "weekday": "MONDAY",
      "is_open": true,
      "windows": [
        {"opens_at": "08:00", "closes_at": "13:00"}
      ]
    },
    {
      "weekday": "SUNDAY",
      "is_open": false,
      "windows": []
    }
  ],
  "confirm_invalidation": false,
  "notify_users": false
}
```

O exemplo omite os outros cinco itens apenas por brevidade; a requisição real exige os sete. `TEMPORARY` exige `valid_until`. Criação, preview e alteração de calendário futuro exigem `valid_from` posterior a hoje. Calendários ativos do mesmo tipo não podem sobrepor. `PATCH` é aceito somente para configuração futura; calendário iniciado usa `replace/` com `effective_from` posterior a hoje. Emergência no próprio dia usa `CalendarException`.

O preview recebe os dados do calendário proposto e devolve:

```json
{
  "affected_period": {
    "starts_on": "2026-12-21",
    "ends_on": "2027-01-31"
  },
  "conflicting_reservations": [
    {
      "id": 84,
      "user_reference": "202312345",
      "computer_id": 3,
      "starts_at": "2026-12-22T18:00:00-05:00",
      "ends_at": "2026-12-22T18:15:00-05:00",
      "reason": "OUTSIDE_NEW_OPERATING_HOURS"
    }
  ],
  "total": 1
}
```

Sem `confirm_invalidation=true`, a aplicação responde `SCHEDULE_CHANGE_AFFECTS_RESERVATIONS` e reverte a mudança. Com confirmação, as reservas conflitantes ficam `INVALIDATED` e calendário, auditorias e aviso opcional são confirmados juntos.

### Status da sala e avisos

```text
GET /api/room-status/?date=YYYY-MM-DD

GET /api/room-notices/active/
GET  /api/room-notices/
POST /api/room-notices/
GET   /api/room-notices/{id}/
PATCH /api/room-notices/{id}/
```

`room-status` e `room-notices/active` são públicos e funcionam antes da escolha de perfil. Os demais endpoints de aviso são restritos ao Supervisor e Administrador.

```json
{
  "date": "2026-08-09",
  "status": "CLOSED",
  "source": "REGULAR_SCHEDULE",
  "is_open_now": false,
  "reason": "A Sala de Informática não funciona aos domingos.",
  "operating_windows": [],
  "active_notices": []
}
```

Um aviso possui tipo `CLOSURE`, `SCHEDULE_CHANGE` ou `SPECIAL_HOURS`, período efetivo, período de visibilidade e flag ativa. Criação de calendário ou exceção aceita `notify_users=true` e objeto `notice`; ambos são salvos ou revertidos na mesma transação.

### Reservas

```text
GET  /api/reservations/
GET  /api/reservations/mine/
POST /api/reservations/
POST /api/reservations/{id}/cancel/
```

`POST /reservations/` é exclusivo do Usuário da Sala e recebe:

```json
{
  "computer_id": 12,
  "starts_at": "2026-08-07T09:00:00-05:00",
  "slot_count": 4
}
```

O início deve estar alinhado à grade da janela operacional. O backend calcula `ends_at=10:00`, `check_in_deadline_at=09:03` e `exit_deadline_at=10:03`, validando todo o intervalo consecutivo. A resposta inclui esses campos, `no_show_at` e o `slot_count` derivado. `mine/` lista apenas as reservas do contexto atual. A listagem geral e o cancelamento de terceiros são operacionais; reservas canceladas deixam de bloquear o intervalo.
Cancelamento de terceiro exige justificativa e gera evento de auditoria.

Reservas invalidadas expõem `invalidated_at`, `invalidated_by_profile` e `invalidation_reason`. Elas permanecem em `mine/`, deixam de bloquear slots e não podem iniciar sessão. Entrada é aceita somente entre `starts_at` e `check_in_deadline_at`, inclusive; depois disso a reconciliação registra `NO_SHOW` e `no_show_at`.

### Sessões e alocações

```text
GET  /api/usage-sessions/current/
GET  /api/usage-sessions/active/
GET  /api/usage-sessions/history/
POST /api/usage-sessions/start/
POST /api/usage-sessions/{id}/switch-computer/
POST /api/usage-sessions/{id}/finish/
```

Uso imediato recebe computador e duração:

```json
{
  "computer_id": 12,
  "slot_count": 2
}
```

Se a entrada ocorrer às 08h21, a sessão responde com `planned_starts_at=08:21`, `planned_ends_at=08:51` e `exit_deadline_at=08:54`. O intervalo inteiro deve caber antes do fechamento e não pode invadir reserva confirmada ou sessão planejada.

Entrada com reserva recebe `computer_id` e `reservation_id`; enviar também `slot_count` é erro 400. A sessão herda snapshots, intervalo e deadlines da reserva. Entrada antecipada é rejeitada e entrada atrasada não desloca o fim planejado.

Troca encerra a alocação atual e cria a próxima na mesma sessão depois de validar o destino até `planned_ends_at`; é rejeitada durante a tolerância. Saída antecipada ou exatamente no prazo é aceita. Saída operacional de terceiro exige justificativa e auditoria. Sessões vencidas são encerradas em `exit_deadline_at` com alocação `TIME_LIMIT_REACHED`.

O comando periódico é:

```text
python manage.py reconcile_operational_deadlines
```

Ele deve ser agendado externamente a cada minuto, encerra sessões com `now >= exit_deadline_at` e marca reservas como `NO_SHOW` quando `now > check_in_deadline_at`. Entrada e troca também reconciliam os computadores envolvidos antes de prosseguir; na entrada, isso inclui computadores com sessão ativa ou reserva vencida do próprio usuário.

```text
POST /api/usage-sessions/{id}/correct/
```

A correção é restrita a perfis operacionais, exige justificativa e altera somente entrada, saída ou o último intervalo. A primeira e a última alocação são sincronizadas quando aplicável, toda a linha do tempo é validada e a mudança gera `AuditEvent`.

### Ocorrências

```text
GET   /api/occurrences/
POST  /api/occurrences/
GET   /api/occurrences/{id}/
PATCH /api/occurrences/{id}/
```

Usuário da Sala consulta apenas as próprias ocorrências. Perfis operacionais consultam todas e realizam as transições de análise, resolução ou cancelamento. Computador, sessão e alocação devem ser compatíveis; criar ocorrência não altera o estado operacional do computador.

### Relatórios

```text
GET /api/reports/monthly/?year=YYYY&month=M
```

O relatório mensal é restrito ao Supervisor e Administrador. A resposta contém todos os dias do mês, `calendar_status`, `calendar_source`, `operating_minutes`, colunas por `Shift.series_key`, totais por turno e as métricas de visitas, pessoas distintas, reservas totais e `reservations_by_status`, ocorrências, computadores utilizados, minutos operacionais, minutos alocados e tempo médio das sessões finalizadas. Sessões sem turno são agrupadas em `NOT_INFORMED`.

## Endpoints planejados

### Relatórios

```text
GET /api/reports/daily/
GET /api/reports/annual/
GET /api/reports/occupancy/
```

O relatório semanal permanece como evolução futura e não possui endpoint definido na Etapa 4.

## Formato de erro

```json
{
  "code": "DATE_OUTSIDE_ALLOWED_WINDOW",
  "detail": "A data deve ser hoje ou amanhã.",
  "fields": {}
}
```

A API não deve expor endpoints genéricos que permitam alterar diretamente estados de reserva, sessão ou alocação sem executar as invariantes do caso de uso.
