# ADR 0024: Ampliar a janela de check-in de reservas

## Status

Aceita.

## Contexto

A ADR 0019 limitava a entrada vinculada a uma reserva ao intervalo entre o início planejado e três minutos depois dele. A operação passou a exigir a mesma tolerância de três minutos antes do início, sem converter essa margem em duração reservada ou disponibilidade planejada.

O domínio já registra automaticamente a saída de sessões vencidas por meio da reconciliação periódica em `exit_deadline_at`. Essa consequência deve permanecer explícita para o usuário: ultrapassado o prazo máximo de saída, a sessão e sua alocação são encerradas com o horário limite, sem depender de uma ação manual.

## Decisão

Uma reserva confirmada aceita check-in no intervalo fechado `[starts_at - 3 minutos, check_in_deadline_at]`, respeitados o funcionamento efetivo da sala e o estado do computador. A entrada antecipada registra `started_at` e o início da primeira alocação no instante real, mas preserva `planned_starts_at`, `planned_ends_at` e `exit_deadline_at` copiados da reserva.

A tolerância continua fixa em `operations/rules.py`, não é configurável na `BookingPolicy` e não cria novo campo persistido: o início da janela é derivado de `starts_at`. A constraint de `UseSession` aceita a antecipação somente quando há reserva vinculada. Uso imediato continua começando no instante da confirmação.

Quando `now >= exit_deadline_at`, a reconciliação registra a saída automaticamente, encerra a sessão e a alocação em `exit_deadline_at`, define `TIME_LIMIT_REACHED` e registra `SYSTEM_ADMIN` como perfil de saída. O comando `reconcile_operational_deadlines` permanece a rotina a ser agendada externamente a cada minuto.

Esta decisão substitui apenas a proibição de check-in antecipado da ADR 0019.

## Consequências

- o usuário pode registrar entrada até três minutos antes ou depois do início reservado;
- intervalos planejados, disponibilidade futura e duração solicitada não são deslocados;
- API e interface podem apresentar a janela a partir de `starts_at` e `check_in_deadline_at`, sem novo atributo de contrato;
- a migration atualiza a barreira de integridade para a mesma janela aplicada pelo serviço;
- o ambiente implantado precisa manter a reconciliação periódica ativa para registrar a saída automática no prazo.
