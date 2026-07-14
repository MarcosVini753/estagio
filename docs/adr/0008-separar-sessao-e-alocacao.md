# ADR 0008: Separar sessão de uso e alocação de computador

## Status

Aceita

## Contexto

O usuário pode trocar de computador durante uma visita. Armazenar apenas um computador na sessão apagaria o histórico ou obrigaria a criar várias sessões para a mesma visita.

## Decisão

Representar a visita em `UseSession` e cada intervalo de uso de máquina em `ComputerAllocation`.

## Alternativas consideradas

- guardar `computer_id` diretamente na sessão;
- criar nova sessão a cada troca;
- armazenar trocas em JSON sem integridade relacional.

## Consequências positivas

- preserva histórico completo;
- uma visita continua sendo uma única sessão;
- permite calcular tempo por computador;
- torna relatórios e ocorrências mais precisos.

## Consequências negativas e riscos

- entrada, troca e saída exigem transações envolvendo duas entidades;
- deve existir no máximo uma alocação ativa por sessão e por computador;
- consultas simples precisam carregar a alocação atual.
