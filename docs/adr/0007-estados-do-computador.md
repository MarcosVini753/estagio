# ADR 0007: Separar estado operacional e estado efetivo do computador

## Status

Aceita

## Contexto

O protótipo usa estados como disponível, ocupado, reservado e bloqueado. Persistir todos esses valores criaria inconsistências, pois ocupação e reserva dependem do tempo e de outros registros.

## Decisão

Persistir apenas `AVAILABLE`, `MAINTENANCE` e `INACTIVE`. Calcular `OCCUPIED` por alocação ativa e `RESERVED` por reserva válida no intervalo consultado.

## Alternativas consideradas

- persistir todos os estados em um único campo;
- manter estados separados para hoje e amanhã;
- recalcular e gravar estado por tarefa agendada.

## Consequências positivas

- elimina fontes duplicadas de verdade;
- representa corretamente estados temporais;
- evita tarefas de sincronização;
- facilita consultas históricas quando combinado com eventos operacionais.

## Consequências negativas e riscos

- consultas de disponibilidade ficam mais complexas;
- relatórios exigem joins e intervalos;
- toda interface deve informar o instante ou período da consulta.
