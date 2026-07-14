# ADR 0009: Permitir reserva somente para amanhã

## Status

Aceita

## Contexto

O fluxo definido distingue uso imediato e reserva antecipada. A consulta deve ser simples e limitada a hoje e amanhã.

## Decisão

Permitir uso imediato hoje e criação de reservas apenas para amanhã. Horários já passados no dia atual são rejeitados. Outras datas ficam fora da janela permitida.

## Alternativas consideradas

- reservar também para hoje;
- agenda para qualquer data futura;
- permitir somente uso imediato, sem reservas.

## Consequências positivas

- regra simples para usuários e biblioteca;
- reduz conflitos e complexidade de calendário;
- mantém o MVP alinhado ao fluxo validado.

## Consequências negativas e riscos

- um horário futuro de hoje apenas consultado não fica garantido;
- expansão da janela exigirá revisão de regras, interface e testes;
- o backend deve validar a data, sem confiar no frontend.
