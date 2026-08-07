# ADR 0022: Versionar políticas de reserva e vinculá-las às reservas

## Status

Aceita.

## Contexto

`BookingPolicy.is_active` tornava versões antigas indisponíveis para consultas normais. Além disso, o cancelamento procurava novamente a política pela data da reserva, permitindo que uma alteração administrativa mudasse retroativamente a regra aplicada a um compromisso existente.

## Decisão

`BookingPolicy` usa vigência inclusiva `valid_from` e `valid_until`, sem `is_active`. Uma exclusion constraint PostgreSQL impede sobreposição e um selector resolve a versão que contém a data consultada.

Ao atualizar a política atual, o serviço encerra sua vigência no dia anterior e cria uma nova versão. Uma versão já ligada a reservas é imutável; se ela começou hoje, a nova versão começa amanhã. Uma versão de hoje ou futura ainda sem reservas pode ser ajustada sem criar outra linha.

`Reservation.booking_policy` é uma chave estrangeira obrigatória com `PROTECT`. A criação persiste a versão vigente e o cancelamento usa diretamente esse vínculo. O backfill escolhe a versão aplicável na data inicial da reserva antes de impor `NOT NULL`.

## Consequências

- políticas antigas permanecem recuperáveis;
- condições de cancelamento não mudam retroativamente;
- políticas referenciadas não podem ser apagadas;
- a migration precisa ordenar e fechar as versões existentes antes de criar a constraint de não sobreposição.
