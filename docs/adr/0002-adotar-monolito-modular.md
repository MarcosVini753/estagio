# ADR 0002: Adotar monólito modular

## Status

Aceita

## Contexto

Reservas, sessões, alocações, estados de computador e relatórios compartilham transações e o mesmo banco. A carga prevista é pequena e o projeto possui escopo acadêmico e institucional limitado.

## Decisão

Implementar uma única aplicação Django organizada em apps por domínio.

## Alternativas consideradas

- microsserviços;
- monólito em um único app Django;
- backend separado por processos independentes.

## Consequências positivas

- implantação simples;
- transações atômicas entre domínios;
- menor custo operacional;
- evolução incremental por módulo;
- menor risco de inconsistência distribuída.

## Consequências negativas e riscos

- os limites entre apps precisam ser respeitados;
- imports circulares devem ser evitados;
- `core` não pode virar depósito de regras sem domínio claro;
- uma futura divisão em serviços exigiria trabalho explícito de extração.
