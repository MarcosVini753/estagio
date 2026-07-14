# ADR 0009: Janela temporal para reservas e uso imediato

## Status

Aceita

## Contexto

A consulta deve permanecer simples e limitada a hoje e amanhã, distinguindo uso imediato de bloqueio antecipado de horário.

## Decisão

Permitir uso imediato somente hoje. Permitir reservas para horários futuros do dia corrente ou para amanhã. Horários já iniciados ou passados hoje são rejeitados. Datas anteriores e posteriores a amanhã ficam fora da janela.

## Alternativas consideradas

- reserva somente para amanhã;
- agenda para qualquer data futura;
- somente uso imediato, sem reservas.

## Consequências positivas

- mantém a janela simples;
- permite garantir horário futuro no mesmo dia;
- reduz complexidade de calendário;
- mantém regras fáceis de validar no backend.

## Consequências negativas e riscos

- o backend precisa considerar o horário atual e o timezone de Rio Branco;
- a interface não pode ser fonte de validação;
- expansão da janela exigirá revisão de regras, testes e interface.
