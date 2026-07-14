# ADR 0012: Remover fila de espera do escopo

## Status

Aceita

## Contexto

A fila de espera aparecia em versões anteriores do contexto e do MVP, mas foi retirada da direção atual do projeto.

## Decisão

Não implementar fila de espera, entradas em fila, posição, chamada de usuário, tempo de espera ou métricas relacionadas.

## Alternativas consideradas

- manter fila no MVP;
- manter entidade sem interface;
- adiar somente a interface e preservar referências em relatórios.

## Consequências positivas

- reduz escopo e complexidade;
- simplifica disponibilidade e relatórios;
- evita entidades e estados sem uso validado.

## Consequências negativas e riscos

- a ausência de computador disponível apenas será informada ao usuário;
- eventual retorno da funcionalidade exigirá nova análise, documentação e ADR;
- agentes devem remover referências antigas em documentação e não inferir a funcionalidade a partir de versões históricas.
