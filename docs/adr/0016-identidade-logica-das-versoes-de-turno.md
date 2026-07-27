# ADR 0016: Identidade lógica das versões de turno

## Status

Aceita.

## Contexto

A substituição de um turno cria uma nova linha para preservar os horários históricos. Sem uma identidade estável, versões do mesmo turno seriam tratadas como colunas distintas nos relatórios.

## Decisão

Adicionar `Shift.series_key` como UUID indexado e imutável. Uma substituição copia a chave da versão anterior. A migration agrupa registros existentes por `(name, display_order)`.

## Consequências

- relatórios agrupam versões históricas do mesmo turno;
- turnos lógicos distintos mantêm chaves diferentes;
- nome, horário e vigência continuam pertencendo a cada versão.
