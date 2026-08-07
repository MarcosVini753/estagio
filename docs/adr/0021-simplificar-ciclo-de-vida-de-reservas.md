# ADR 0021: Simplificar o ciclo de vida de reservas

## Status

Aceita.

## Contexto

`NO_SHOW` e `INVALIDATED` representavam causas diferentes para uma mesma consequência operacional: a reserva deixava de ser utilizável e de bloquear o computador. Isso duplicava campos de instante, perfil e motivo, serviços, serializers, relatórios e nomes de confirmação do calendário.

## Decisão

`Reservation` terá somente os estados `CONFIRMED`, `CANCELLED` e `USED`.

Expiração do prazo de check-in passa de `CONFIRMED` para `CANCELLED`, com `cancelled_by_profile=SYSTEM_ADMIN`, instante de reconciliação e motivo “Prazo de check-in expirado.” Mudança de calendário incompatível e indisponibilidade de computador sem alternativa também usam cancelamento administrativo.

O helper interno `cancel_locked_reservation()` centraliza apenas a escrita final e a auditoria. Autorização, limite temporal e escolha do motivo continuam nos fluxos chamadores. A confirmação do calendário chama-se `confirm_cancellation`, e os serviços usam linguagem de cancelamento.

Migrations convertem `NO_SHOW` e `INVALIDATED` sem perder autor, instante ou motivo antes de remover `no_show_at`, `invalidated_at`, `invalidated_by_profile` e `invalidation_reason`.

Esta decisão substitui apenas as partes das ADRs 0017 e 0019 que definiam `INVALIDATED` e `NO_SHOW`.

## Consequências

- disponibilidade e check-in dependem de três estados estáveis;
- relatórios agregam apenas confirmadas, canceladas e usadas;
- a causa continua preservada nos metadados e eventos de auditoria;
- clientes devem trocar `confirm_invalidation` por `confirm_cancellation` e remover campos de invalidação/não comparecimento.
