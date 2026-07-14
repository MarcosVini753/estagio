# API v1

## Política de versionamento

A API começa em `/api/v1/`. A versão da API é independente da versão da aplicação. Novos campos opcionais e endpoints compatíveis permanecem em v1; mudanças incompatíveis exigem migração planejada ou nova versão.

## Convenções

- JSON em `snake_case`;
- datas e horários em ISO 8601 com timezone;
- filtros por query string;
- erros com `code`, `detail` e `fields`;
- OpenAPI gerado com `drf-spectacular`;
- operações de domínio expostas como actions explícitas;
- endpoints protegidos pelo perfil de demonstração armazenado na sessão.

## Endpoints implementados

### Sistema e demonstração

```text
GET  /api/v1/health/
GET  /api/v1/demo/context/
POST /api/v1/demo/select-profile/
```

A seleção de perfil simula autorização e não autentica uma identidade real.

### Computadores

```text
GET   /api/v1/computers/
POST  /api/v1/computers/
GET   /api/v1/computers/{id}/
PATCH /api/v1/computers/{id}/
PATCH /api/v1/computers/{id}/operational-state/
```

Leitura é permitida para qualquer perfil selecionado. Cadastro e edição são permitidos ao Supervisor e Administrador. A alteração de estado operacional também é permitida ao Estagiário e sempre registra histórico.

O PATCH genérico não altera `operational_state`; a action específica deve ser usada para preservar auditoria e validações.

### Disponibilidade

```text
GET /api/v1/computers/availability/?date=YYYY-MM-DD
GET /api/v1/computers/{id}/slots/?date=YYYY-MM-DD
```

A data deve ser hoje ou amanhã. O primeiro endpoint devolve um resumo por computador:

```json
{
  "date": "2026-07-14",
  "is_today": true,
  "slot_duration_minutes": 60,
  "generated_at": "2026-07-14T09:30:00-05:00",
  "computers": [
    {
      "id": 1,
      "code": "PC-01",
      "description": "Computador da Sala de Informática",
      "operational_state": "AVAILABLE",
      "effective_status_now": "OCCUPIED",
      "can_start_now": false,
      "available_slot_count": 4,
      "next_available_slot": {
        "starts_at": "2026-07-14T10:15:00-05:00",
        "ends_at": "2026-07-14T11:15:00-05:00"
      }
    }
  ]
}
```

`effective_status_now` é preenchido somente para hoje. Para amanhã, seu valor é `null`; a disponibilidade deve ser consultada pelos slots.

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
  "slot_duration_minutes": 60,
  "slots": [
    {
      "starts_at": "2026-07-15T07:15:00-05:00",
      "ends_at": "2026-07-15T08:15:00-05:00",
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

### Configuração operacional

```text
GET   /api/v1/shifts/
POST  /api/v1/shifts/
GET   /api/v1/shifts/{id}/
PATCH /api/v1/shifts/{id}/

GET   /api/v1/calendar-exceptions/
POST  /api/v1/calendar-exceptions/
GET   /api/v1/calendar-exceptions/{id}/
PATCH /api/v1/calendar-exceptions/{id}/

GET   /api/v1/booking-policy/
PATCH /api/v1/booking-policy/
```

Leitura é permitida para os perfis selecionados. Escrita é permitida ao Supervisor e Administrador. Atualizar a política cria uma nova versão quando a versão vigente começou em data anterior ao dia atual.

## Endpoints planejados

### Reservas

```text
GET  /api/v1/reservations/
GET  /api/v1/reservations/mine/
POST /api/v1/reservations/
POST /api/v1/reservations/{id}/cancel/
```

### Sessões e alocações

```text
GET  /api/v1/usage-sessions/current/
GET  /api/v1/usage-sessions/active/
GET  /api/v1/usage-sessions/history/
POST /api/v1/usage-sessions/start/
POST /api/v1/usage-sessions/{id}/switch-computer/
POST /api/v1/usage-sessions/{id}/finish/
POST /api/v1/usage-sessions/{id}/correct/
```

### Ocorrências e relatórios

```text
GET   /api/v1/occurrences/
POST  /api/v1/occurrences/
PATCH /api/v1/occurrences/{id}/

GET /api/v1/reports/daily/
GET /api/v1/reports/weekly/
GET /api/v1/reports/monthly/
GET /api/v1/reports/annual/
GET /api/v1/reports/occupancy/
```

## Formato de erro

```json
{
  "code": "DATE_OUTSIDE_ALLOWED_WINDOW",
  "detail": "A data deve ser hoje ou amanhã.",
  "fields": {}
}
```

A API não deve expor endpoints genéricos que permitam alterar diretamente estados de reserva, sessão ou alocação sem executar as invariantes do caso de uso.
