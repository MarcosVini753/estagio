# API v1

## Política de versionamento

A API começa em `/api/v1/`. A versão aparece no caminho para facilitar roteamento, documentação, testes e evolução do frontend.

A versão da API é independente da versão da aplicação. Novos campos opcionais e endpoints compatíveis permanecem em v1. Mudanças incompatíveis exigem migração planejada ou nova versão.

## Convenções

- JSON em `snake_case`;
- datas e horários em ISO 8601 com timezone;
- paginação nas listagens históricas;
- filtros por query string;
- erros com `code`, `detail` e `fields` quando aplicável;
- OpenAPI gerado com `drf-spectacular`;
- operações de domínio expostas como actions explícitas, não como atualizações arbitrárias de estado.

## Contexto de demonstração

```text
GET  /api/v1/demo/context/
POST /api/v1/demo/select-profile/
```

Exemplo:

```json
{
  "profile": "INTERN"
}
```

Esse endpoint não autentica o usuário. Apenas altera o contexto de teste.

## Computadores e disponibilidade

```text
GET   /api/v1/computers/
GET   /api/v1/computers/{id}/
POST  /api/v1/computers/
PATCH /api/v1/computers/{id}/
PATCH /api/v1/computers/{id}/operational-state/
GET   /api/v1/computers/availability/?date=YYYY-MM-DD
GET   /api/v1/computers/{id}/slots/?date=YYYY-MM-DD
```

Resposta de disponibilidade:

```json
{
  "id": 4,
  "code": "PC-04",
  "operational_state": "AVAILABLE",
  "effective_status": "RESERVED",
  "reserved_by_current_user": false,
  "can_start_now": false
}
```

## Reservas

```text
GET  /api/v1/reservations/
GET  /api/v1/reservations/mine/
POST /api/v1/reservations/
POST /api/v1/reservations/{id}/cancel/
```

Criação aceita somente intervalo de amanhã.

## Sessões e alocações

```text
GET  /api/v1/usage-sessions/current/
GET  /api/v1/usage-sessions/active/
GET  /api/v1/usage-sessions/history/
POST /api/v1/usage-sessions/start/
POST /api/v1/usage-sessions/{id}/switch-computer/
POST /api/v1/usage-sessions/{id}/finish/
POST /api/v1/usage-sessions/{id}/correct/
```

Não expor endpoint genérico que permita mudar diretamente o status da sessão sem executar as invariantes do caso de uso.

## Ocorrências

```text
GET   /api/v1/occurrences/
POST  /api/v1/occurrences/
GET   /api/v1/occurrences/{id}/
PATCH /api/v1/occurrences/{id}/
```

## Configurações

```text
GET   /api/v1/shifts/
POST  /api/v1/shifts/
PATCH /api/v1/shifts/{id}/
GET   /api/v1/calendar-exceptions/
POST  /api/v1/calendar-exceptions/
GET   /api/v1/booking-policy/
PATCH /api/v1/booking-policy/
GET   /api/v1/report-configuration/
PATCH /api/v1/report-configuration/
```

## Relatórios

```text
GET /api/v1/reports/daily/
GET /api/v1/reports/weekly/
GET /api/v1/reports/monthly/
GET /api/v1/reports/annual/
GET /api/v1/reports/occupancy/
GET /api/v1/reports/computers/
GET /api/v1/reports/affiliations/
GET /api/v1/reports/occurrences/
```

Exportação:

```text
GET /api/v1/reports/monthly/export/?year=2026&month=7&format=csv
```

## Formato de erro

```json
{
  "code": "COMPUTER_NOT_AVAILABLE",
  "detail": "O computador não está disponível no intervalo solicitado.",
  "fields": {}
}
```

## Perfis e acesso simulado

Os endpoints verificam o perfil armazenado na sessão de demonstração para ocultar ou impedir ações incompatíveis. Isso não substitui segurança. Antes de usar dados reais, todos os endpoints devem migrar para autenticação e autorização reais.
