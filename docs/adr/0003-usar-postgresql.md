# ADR 0003: Usar PostgreSQL como banco-alvo

## Status

Aceita

## Contexto

O sistema precisa de integridade relacional, constraints condicionais, controle de concorrência e consultas agregadas para relatórios.

## Decisão

Usar PostgreSQL como banco-alvo do projeto. SQLite pode ser usado apenas em experimentos locais muito iniciais, sem validar comportamento concorrente ou constraints específicas.

## Alternativas consideradas

- SQLite em todas as etapas;
- MySQL ou MariaDB;
- banco NoSQL.

## Consequências positivas

- suporte robusto a transações e bloqueios;
- constraints avançadas para sessões, alocações e reservas;
- consultas temporais e agregações adequadas;
- maior proximidade entre desenvolvimento integrado e produção.

## Consequências negativas e riscos

- exige serviço de banco no ambiente local;
- testes de integração precisam executar em PostgreSQL;
- recursos específicos devem ser documentados para evitar dependência acidental sem teste.
