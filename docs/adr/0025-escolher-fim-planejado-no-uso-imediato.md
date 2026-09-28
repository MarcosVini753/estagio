# ADR 0025: Escolher fim planejado no uso imediato

## Status

Aceita.

Substitui somente a decisão da ADR 0019 que fazia o uso imediato receber
`slot_count` e derivar seu fim pela duração. As decisões sobre intervalos
planejados, tolerâncias operacionais, alocações e reconciliação continuam
vigentes.

## Contexto

O uso imediato começa no instante real em que a pessoa confirma a entrada. Por
isso, somar slots de quinze minutos ao instante atual cria fins desalinhados à
grade da sala: uma entrada às 08h21 terminaria às 08h51. Isso dificulta a
leitura da agenda e permite que uma troca pareça alterar o compromisso inicial.

## Decisão

Uso imediato recebe `planned_ends_at`, não `slot_count`. O início real e o
início planejado são `now`; a pessoa escolhe um fim na grade global diária
`07:15 + N × 15 minutos`, estritamente posterior à entrada, dentro da mesma
janela operacional. O fim pode coincidir com fechamento ou início de reserva
quando esse limite pertence à grade; diante de um limite irregular, como
13h10, a última opção é a marca anterior, 13h00.

O backend calcula as opções no detalhe do computador e revalida a escolha na
transação. A lista de disponibilidade expõe apenas `can_start_now`,
`max_planned_ends_at` e `limited_by`; o detalhe inclui
`planned_end_options`. Reservas continuam recebendo `slot_count`.

`exit_deadline_at` continua sendo o fim planejado mais três minutos, para
operação, auditoria e reconciliação. A área do Usuário da Sala apresenta o
horário real de entrada e o fim planejado, sem revelar tolerâncias. A troca de
computador preserva `planned_ends_at` e `exit_deadline_at` da mesma sessão.

## Consequências

- a pessoa escolhe um horário de saída reconhecível, inclusive após entrada
  entre marcas da grade;
- conflitos seguem sendo decididos pelo backend, inclusive em concorrência;
- clientes que iniciam uso imediato devem enviar `planned_ends_at`; payloads
  legados com `slot_count` recebem erro de validação;
- não há migration: os horários já persistidos permanecem históricos.
