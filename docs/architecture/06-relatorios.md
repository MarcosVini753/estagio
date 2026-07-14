# Arquitetura de relatórios

## Princípio

Relatórios são projeções derivadas dos registros operacionais. Não haverá tabela de lançamentos manuais com totais desconectados das sessões.

## Fontes

- `UseSession`: visita, entrada, saída, duração e usuário de demonstração;
- `ComputerAllocation`: computador utilizado, intervalo e trocas;
- `Reservation`: confirmadas, canceladas, usadas e não comparecimentos;
- `Occurrence`: problemas por computador e período;
- `Shift`: classificação temporal;
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

### Reservas

Contagem por estado: confirmada, cancelada, usada, não comparecida e invalidada.

### Ocorrências

Contagem por estado, computador e período.

## Turnos

- total de visitas: turno da entrada da sessão;
- tempo de ocupação: distribuir alocações pelos turnos que atravessarem;
- reservas: classificar pelo intervalo reservado;
- alterações de configuração devem respeitar validade temporal.

## Relatório diário

Deve apresentar:

- data;
- totais por turno;
- total geral;
- sessões e usuários distintos;
- computadores utilizados;
- ocorrências relevantes.

## Relatório semanal

Consolida os dias da semana e permite comparação por turno.

## Relatório mensal

Deve reproduzir o modelo atual:

- linhas por dia;
- colunas por turno;
- totais por turno;
- total geral mensal;
- referência ao total anual acumulado quando solicitado.

## Relatório anual

Consolida meses, totais por turno, visitas, pessoas distintas e indicadores de ocupação.

## Implementação

Estrutura sugerida:

```text
reports/
├── selectors/
│   ├── sessions.py
│   ├── allocations.py
│   └── reservations.py
├── projections/
│   ├── daily.py
│   ├── monthly.py
│   └── occupancy.py
├── exporters/
│   ├── csv.py
│   ├── xlsx.py
│   └── pdf.py
└── api/v1/
```

## Exportação

Prioridade:

1. CSV;
2. XLSX;
3. PDF.

A exportação deve usar a mesma projeção exibida na API para evitar totais divergentes.

## Desempenho

No MVP, consultas agregadas diretas são suficientes. Materialized views, snapshots e processamento assíncrono só devem ser introduzidos após medição e novo ADR.
