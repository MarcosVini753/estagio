# ADR 0014: Identidade fictícia e snapshots analíticos

## Status

Aceita

## Contexto

O perfil de demonstração sozinho não diferencia usuários da sala nem permite agrupamento histórico por vínculo e unidade. O MVP não possui autenticação e não deve persistir contas reais.

## Decisão

Armazenar referência fictícia, tipo de vínculo e unidade institucional na sessão Django quando o perfil for `ROOM_USER`. Copiar vínculo e unidade para `Reservation` e `UseSession` no momento da criação. Registros anteriores usam `NOT_INFORMED` e unidade vazia.

## Consequências

- relatórios históricos não dependem do contexto atual;
- os dados continuam fictícios e não comprovam identidade;
- não há conta, senha, token ou integração institucional.
