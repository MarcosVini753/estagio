# Arquitetura de relatórios

## Princípio

Relatórios são projeções derivadas dos registros operacionais. Não haverá tabela de lançamentos manuais com totais desconectados das sessões.

## Dados históricos de demonstração

```bash
python manage.py seed_report_demo_data --days 60 --seed 12345 --reset
```

O comando cria uma linha do tempo fictícia determinística e informa no terminal as datas inicial e final geradas. Referências usam o prefixo reservado `demo-report-`; `--reset` remove somente registros operacionais e sentinelas criados pelo comando. Computadores, turnos e configurações existentes nunca são sobrescritos ou removidos.

## Fontes

- `UseSession`: visita, entrada, saída, duração e usuário de demonstração;
- `ComputerAllocation`: computador utilizado, intervalo e trocas;
- `Reservation`: confirmadas, canceladas, usadas e não comparecimentos;
- `Occurrence`: problemas por computador e período;
- `Shift`: classificação temporal;
- calendário operacional efetivo: dias, janelas e denominador de funcionamento;
- `ComputerOperationalStateChange`: manutenção e inatividade históricas;
- dados fictícios de curso, setor e vínculo usados no MVP.

Fila de espera não é fonte porque foi removida do escopo.

## Métricas

### Visitas

Quantidade de sessões iniciadas no período. Uma troca de computador não cria nova visita.

### Pessoas distintas

Quantidade de referências de usuário distintas no período. Deve ser exibida separadamente de visitas.

### Uso por computador

Baseado em alocações. Uma sessão com troca contribui para mais de um computador.

### Tempo médio de permanência

Média da duração das sessões finalizadas. Sessões ativas ou inconsistentes devem ser sinalizadas.

### Taxa de ocupação

```text
tempo total alocado
tempo operacional disponível
```

O denominador deve excluir manutenção, inatividade e períodos sem funcionamento quando houver dados históricos suficientes.

O calendário é a fonte do período de funcionamento: domingo regular soma zero minuto, sábado regular termina às 13h, horário temporário substitui o regular durante sua vigência e exceção específica tem precedência. `Shift` permanece somente como dimensão analítica.

### Reservas

Contagem por estado: confirmada, cancelada, usada, não comparecida e invalidada.

### Ocorrências

Contagem por estado, computador e período.

## Turnos

- total de visitas: turno da entrada da sessão;
- tempo de ocupação: distribuir alocações pelos turnos que atravessarem;
- reservas: classificar pelo intervalo reservado;
- alterações de configuração devem respeitar validade temporal.
- versões do mesmo turno lógico são agrupadas por `Shift.series_key`.

Todos os períodos usam `America/Rio_Branco` e limites `[start, end)`. Intervalos de alocação são recortados ao período consultado. Para sessões ativas, o fim temporário é `min(now, period_end)`; elas não entram no tempo médio de permanência.

## Relatório diário

Deve apresentar:

- data;
- totais por turno;
- total geral;
- sessões e usuários distintos;
- computadores utilizados;
- ocorrências relevantes.

## Relatório mensal

Implementado em:

```text
GET /api/v1/reports/monthly/?year=YYYY&month=M
```

O endpoint é restrito ao Supervisor e Administrador e reproduz o modelo atual:

- linhas por dia;
- colunas por `series_key`;
- totais por turno;
- total geral mensal;
- dias sem uso;
- estado de calendário `OPEN`, `CLOSED` ou `SPECIAL_HOURS`;
- origem `REGULAR_SCHEDULE`, `TEMPORARY_SCHEDULE` ou `CALENDAR_EXCEPTION`;
- minutos operacionais calculados pelas janelas efetivas de cada dia;
- grupo `NOT_INFORMED` para sessões sem turno.

As métricas complementares são visitas, pessoas distintas, reservas totais e por estado (inclusive `INVALIDATED`), ocorrências pela criação, computadores utilizados, minutos operacionais, minutos alocados e tempo médio de sessões finalizadas. Uma sessão com troca continua sendo uma visita, mas suas alocações contribuem para todos os computadores e intervalos utilizados.

## Relatório anual

Consolida meses, totais por turno, visitas, pessoas distintas e indicadores de ocupação.

## Implementação atual

O relatório mensal usa:

```text
Banco → selectors.py → projections.py → API JSON
```

Não há modelo agregado nem exporter nesta entrega.

## Exportação

Prioridade:

1. CSV;
2. XLSX;
3. PDF.

A exportação deve usar a mesma projeção exibida na API para evitar totais divergentes.

## Evolução futura

O relatório semanal não faz parte da Etapa 4. Diário, anual, indicadores, taxa percentual de ocupação e exportações serão adicionados em entregas próprias.

## Desempenho

No MVP, consultas agregadas diretas são suficientes. Materialized views, snapshots e processamento assíncrono só devem ser introduzidos após medição e novo ADR.
