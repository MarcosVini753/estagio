# Modelo entidade-relacionamento

```mermaid
erDiagram
    COMPUTER ||--o{ COMPUTER_OPERATIONAL_STATE_CHANGE : possui
    COMPUTER ||--o{ RESERVATION : recebe
    COMPUTER ||--o{ COMPUTER_ALLOCATION : recebe
    COMPUTER ||--o{ OCCURRENCE : relacionado
    RESERVATION o|--o| USE_SESSION : origina
    USE_SESSION ||--|{ COMPUTER_ALLOCATION : contem
    USE_SESSION ||--o{ OCCURRENCE : relacionado
    COMPUTER_ALLOCATION ||--o{ OCCURRENCE : relacionado
    SHIFT o|--o{ USE_SESSION : classifica
    OPERATING_SCHEDULE ||--|{ OPERATING_SCHEDULE_DAY : configura
    OPERATING_SCHEDULE_DAY ||--o{ OPERATING_WINDOW : possui
    OPERATING_SCHEDULE o|--o{ ROOM_NOTICE : comunica
    CALENDAR_EXCEPTION o|--o{ ROOM_NOTICE : comunica

    COMPUTER {
        bigint id
        string code
        string operational_state
        string asset_number
        datetime created_at
        datetime updated_at
    }

    COMPUTER_OPERATIONAL_STATE_CHANGE {
        bigint id
        bigint computer_id
        string previous_state
        string new_state
        string actor_profile
        string reason
        datetime changed_at
    }

    RESERVATION {
        bigint id
        string user_reference
        string affiliation_type
        string institutional_unit
        bigint computer_id
        datetime starts_at
        datetime ends_at
        string status
        datetime invalidated_at
        string invalidated_by_profile
        string invalidation_reason
    }

    USE_SESSION {
        bigint id
        string user_reference
        string affiliation_type
        string institutional_unit
        bigint reservation_id
        bigint start_shift_id
        datetime started_at
        datetime ended_at
        string status
    }

    COMPUTER_ALLOCATION {
        bigint id
        bigint session_id
        bigint computer_id
        int sequence
        datetime started_at
        datetime ended_at
    }

    OCCURRENCE {
        bigint id
        bigint computer_id
        bigint session_id
        bigint allocation_id
        string status
        string description
    }

    SHIFT {
        bigint id
        uuid series_key
        string name
        time start_time
        time end_time
        date valid_from
        date valid_until
    }

    OPERATING_SCHEDULE {
        bigint id
        uuid series_key
        string name
        string schedule_type
        date valid_from
        date valid_until
        boolean is_active
    }

    OPERATING_SCHEDULE_DAY {
        bigint id
        bigint schedule_id
        int weekday
        boolean is_open
    }

    OPERATING_WINDOW {
        bigint id
        bigint schedule_day_id
        time opens_at
        time closes_at
        int display_order
    }

    CALENDAR_EXCEPTION {
        bigint id
        date date
        string exception_type
        time opens_at
        time closes_at
    }

    ROOM_NOTICE {
        bigint id
        string notice_type
        string title
        date effective_from
        date effective_until
        datetime visible_from
        datetime visible_until
        boolean is_active
    }
```

O diagrama é conceitual. Migrations registram constraints e índices definitivos, inclusive não sobreposição de calendários ativos do mesmo tipo, unicidade de dia por calendário e abertura anterior ao fechamento.
