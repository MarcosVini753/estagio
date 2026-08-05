# ADR 0015: Versionar historicamente os turnos

## Status

Aceita

## Contexto

Sessões guardam a versão de turno usada na entrada. Alterar diretamente os horários de um turno já utilizado altera a interpretação histórica de sessões e relatórios.

## Decisão

Impedir alterações diretas de dados temporais em turnos usados. A substituição ocorre em transação, com início futuro: a versão anterior recebe `valid_until` no dia anterior e uma nova versão é criada com a nova vigência. A operação registra `AuditEvent`.

## Consequências

- sessões antigas continuam apontando para os horários vigentes na entrada;
- turnos futuros sem uso continuam editáveis;
- desativação não apaga registros históricos;
- não há substituição retroativa.
