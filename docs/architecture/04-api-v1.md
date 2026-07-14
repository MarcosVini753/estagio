# API v1

## Política

Todos os endpoints ficam sob `/api/v1/`. JSON usa `snake_case`; datas usam ISO 8601 com timezone; erros usam `code`, `detail` e `fields`.

## Implementado

```text
GET  /api/v1/health/
GET  /api/v1/demo/context/
POST /api/v1/demo/select-profile/
```

A seleção de perfil grava `ROOM_USER`, `INTERN`, `LIBRARY_SUPERVISOR` ou `SYSTEM_ADMIN` na sessão Django. Não autentica ninguém.

Documentação:

```text
GET /api/schema/
GET /api/docs/
GET /api/redoc/
```

## Contratos planejados

### Computadores

```text
GET   /api/v1/computers/
GET   /api/v1/computers/{id}/
POST  /api/v1/computers/
PATCH /api/v1/computers/{id}/
PATCH /api/v1/computers/{id}/operational-state/
GET   /api/v1/computers/availability/?date=YYYY-MM-DD
GET   /api/v1/computers/{id}/slots/?date=YYYY-MM-DD
```

### Reservas

```text
GET  /api/v1/reservations/
GET  /api/v1/reservations/mine/
POST /api/v1/reservations/
POST /api/v1/reservations/{id}/cancel/
```

Criação aceita horário futuro de hoje ou intervalo de amanhã.

### Sessões

```text
GET  /api/v1/usage-sessions/current/
GET  /api/v1/usage-sessions/active/
GET  /api/v1/usage-sessions/history/
POST /api/v1/usage-sessions/start/
POST /api/v1/usage-sessions/{id}/switch-computer/
POST /api/v1/usage-sessions/{id}/finish/
POST /api/v1/usage-sessions/{id}/correct/
```

### Ocorrências, configurações e relatórios

Os contratos permanecem planejados na documentação anterior, mas não devem ser considerados implementados até aparecerem no OpenAPI gerado e possuírem testes.

## Regra de evolução

O OpenAPI gerado é a fonte executável. Mudanças incompatíveis exigem migração planejada ou nova versão.
