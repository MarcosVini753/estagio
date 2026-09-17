# Arquitetura de relatórios

## Princípio

Relatórios são projeções dos registros operacionais. Não existe tabela de
lançamentos manuais ou totais persistidos. API, interface HTML e exportadores
chamam a mesma camada de geração para que uma correção legítima apareça de
forma idêntica em todas as saídas.

Antes de carregar os dados, a geração captura um único `now` e reconcilia os
prazos do período. Os selectors carregam sessões, alocações, reservas,
ocorrências, turnos, calendários e históricos de estado em lote; as projeções
seguintes são puras. Não há cache global, materialized view ou processamento
assíncrono.

```text
Banco → reconciliação → selectors → projections → JSON/HTML/exporters
```

`apps.reports.projections` é um pacote com componentes comuns e projeções
diária, mensal, anual e de indicadores. O ano e o intervalo analítico são
carregados em uma passagem; a quantidade de consultas não cresce com a
quantidade de dias.

## Dados históricos de demonstração

```bash
python manage.py seed_report_demo_data --days 60 --seed 12345 --reset
```

O comando cria uma linha do tempo fictícia determinística e informa as datas
geradas. Referências usam o prefixo `demo-report-`; `--reset` remove apenas os
registros operacionais e sentinelas criados pelo próprio comando. Use somente
em banco descartável.

## Fontes e limites temporais

- `UseSession`: visita, entrada, saída e snapshots fictícios de usuário;
- `ComputerAllocation`: computador, intervalo real e trocas;
- `Reservation`: confirmadas, canceladas e usadas;
- `Occurrence`: problemas por situação, computador e período;
- `Shift`: classificação lógica da entrada;
- calendário operacional efetivo: dias e janelas de funcionamento;
- `Computer.created_at` e `ComputerOperationalStateChange`: capacidade
  disponível histórica.

Todos os períodos usam `America/Rio_Branco` e limites internos `[início, fim)`.
No filtro de indicadores, as duas datas informadas são inclusivas e o intervalo
é limitado a 366 dias. Alocações que atravessam a fronteira são recortadas. Uma
sessão ativa usa temporariamente `min(now, fim do período)` e não participa da
média de permanência.

## Métricas

### Visitas e pessoas

Visita é uma sessão iniciada no período. Trocar de computador não cria outra
visita. Pessoas distintas são deduplicadas pela referência fictícia dentro do
período e nunca são individualizadas nas exportações.

### Turnos

Sessão e seus minutos são agrupados pela identidade lógica
`Shift.series_key` registrada na entrada. Versões históricas do mesmo turno
compartilham a coluna. Ausência de classificação usa `NOT_INFORMED`.

### Tempo e taxa de ocupação

```text
numerador   = alocação real dentro de capacidade elegível
denominador = calendário aberto ∩ estado AVAILABLE de cada computador
```

O cálculo termina em `min(fim do período, now)`, portanto horas futuras não
reduzem a taxa atual. Um computador começa a contribuir em `created_at`;
manutenção e inatividade não entram no denominador. Quando não há denominador,
o percentual é `null`.

O histórico operacional é confiável quando cada mudança declara como
`previous_state` o estado resultante do evento anterior e o último evento é
compatível com o estado persistido. Um computador com sequência inconsistente é
excluído integralmente do numerador e denominador e aparece em `warnings` para
não produzir um percentual aparentemente preciso sobre dados contraditórios.

### Horário de maior uso

As alocações reais são intersectadas com a capacidade elegível e distribuídas
em blocos de 15 minutos. Esse indicador mede movimento observado. O sistema não
afirma medir procura recusada porque não registra fila nem tentativas que não
viraram reserva ou sessão.

### Demais métricas

- permanência média: duração bruta das sessões finalizadas no período;
- uso por computador: alocações, preservando cada trecho de uma troca;
- reservas: contagem por `CONFIRMED`, `CANCELLED` e `USED`;
- ocorrências: contagem por estado, computador e criação no período;
- tempo operacional da sala: soma das janelas do calendário, separado da
  capacidade por computador usada na taxa.

## Visões

### Diário

Apresenta calendário efetivo, janelas, turnos lógicos, `NOT_INFORMED`, totais,
resumo e ocupação para uma data.

### Mensal

Preserva a matriz existente com dias nas linhas, turnos nas colunas, origem e
situação do calendário, minutos operacionais e totais. `occupancy` e avisos de
histórico são campos aditivos ao contrato anterior.

### Anual

Sempre retorna os 12 meses, inclusive os vazios. Pessoas e computadores são
deduplicados no ano; médias e totais são recalculados a partir dos registros
brutos, nunca pela média das médias mensais.

### Indicadores

Agrupa por turno lógico, vínculo, unidade institucional, computador, dia e
bloco de 15 minutos. Também informa maiores movimentos observados e contagens
de reservas e ocorrências por situação.

## Exportação

Diário, mensal, anual e indicadores aceitam CSV, XLSX e PDF. Quando `format` é
omitido, vale `ReportConfiguration.default_format`.

- CSV: UTF-8 com BOM, separador `;` e cabeçalhos em português. Indicadores usam
  a coluna `Seção` para manter um arquivo retangular;
- XLSX: planilha `Resumo` e uma planilha por agrupamento, geradas com
  XlsxWriter;
- PDF: contexto, período, resumo e tabelas multipágina, gerados com ReportLab.

`group_by_shift` e `include_occurrences` alteram somente HTML e arquivos. A API
JSON sempre entrega a projeção completa. Nenhum formato inclui referências
individuais de usuários.

## Desempenho e evolução

Consultas em lote e projeções em memória atendem ao volume do MVP. Cache,
snapshots, materialized views ou tarefas assíncronas só devem ser introduzidos
depois de medição e nova decisão arquitetural. O relatório semanal permanece
fora do escopo.
