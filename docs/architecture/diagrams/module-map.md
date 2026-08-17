# Mapa de módulos

```mermaid
flowchart LR
    access[access]
    config[configuration]
    calendar[configuration/calendar.py<br/>resolvedor único]
    computers[computers]
    operations[operations]
    occurrences[occurrences]
    reports[reports]
    audit[audit]
    core[core]

    core --> access
    core --> config
    config --> calendar
    core --> computers
    core --> operations
    core --> occurrences
    core --> reports
    core --> audit

    access --> operations
    config --> operations
    calendar --> operations
    computers --> operations
    operations --> occurrences
    operations --> reports
    config --> reports
    calendar --> reports
    computers --> reports
    occurrences --> reports
    operations --> audit
    config --> audit
    computers --> audit
```

## Regra de direção

`reports` pode consultar os outros domínios, mas os domínios operacionais não dependem de `reports`. `core` contém apenas elementos compartilhados e não deve se tornar um app genérico para qualquer regra.
