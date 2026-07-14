# ADR 0010: Gerar relatórios como projeções

## Status

Aceita

## Contexto

Os relatórios precisam refletir sessões, computadores utilizados, reservas, ocorrências e turnos. Criar lançamentos manuais de totais produziria divergência entre operação e relatório.

## Decisão

Calcular relatórios diretamente a partir dos registros operacionais. Não criar entidade de lançamento manual de relatório no MVP.

## Alternativas consideradas

- tabela de totais preenchida manualmente;
- snapshots obrigatórios a cada dia;
- planilhas externas como fonte de verdade.

## Consequências positivas

- rastreabilidade até os registros de origem;
- elimina dupla digitação;
- permite gerar diferentes agrupamentos;
- correções operacionais refletem nas projeções.

## Consequências negativas e riscos

- consultas podem ficar mais complexas;
- resultados históricos podem mudar após correção legítima;
- snapshots e materialized views podem ser necessários futuramente, mas somente após medição e novo ADR.
