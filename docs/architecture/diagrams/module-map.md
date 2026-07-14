# Mapa de módulos

```mermaid
flowchart LR
    access[access]
    config[configuration]
    computers[computers]
    operations[operations]
    occurrences[occurrences]
    reports[reports]
    audit[audit]
    core[core]

    core --> access
    core --> config
    core --> computers
    core --> operations
    core --> occurrences
    core --> reports
    core --> audit

    access --> operations
    config --> operations
    computers --> operations
    operations --> occurrences
    operations --> reports
    config --> reports
    computers --> reports
    occurrences --> reports
    operations --> audit
    config --> audit
    computers --> audit
```

## Regra de direção

`reports` pode consultar os outros domínios, mas os domínios operacionais não dependem de `reports`. `core` contém apenas elementos compartilhados e não deve se tornar um app genérico para qualquer regra.
