# ADR 0019: Adotar sessões com duração solicitada

## Status

Aceita parcialmente. A semântica de `NO_SHOW` foi substituída pela ADR 0021, a regra de check-in antecipado pela ADR 0024 e a duração solicitada do uso imediato pela ADR 0025; intervalos planejados e deadlines permanecem vigentes.

## Contexto

Reservas representavam um único slot configurável, enquanto sessões imediatas tinham apenas horários reais de entrada e saída. Uma alocação ativa sem término ocupava todos os horários futuros na projeção de disponibilidade. Como a validação observava somente o instante da entrada ou da troca, uma sessão podia começar pouco antes de uma reserva ou do fechamento sem possuir limite planejado.

O domínio precisa distinguir o compromisso de uso assumido antes da entrada do intervalo real posteriormente registrado. Também precisa tolerar uma saída operacionalmente atrasada sem transformar essa tolerância em disponibilidade planejada.

## Decisão

Adotar o Modelo C, no qual reservas possuem duração solicitada como quantidade inteira de slots consecutivos. O slot é uma regra fixa de 15 minutos e não uma política alterável pelo Supervisor. A forma de escolher o fim de uso imediato foi substituída pela ADR 0025.

`Reservation` mantém `starts_at` e `ends_at`, recebe `slot_count` na criação e persiste `check_in_deadline_at` e `exit_deadline_at`. `UseSession` persiste `planned_starts_at`, `planned_ends_at` e `exit_deadline_at`, além dos horários reais. `slot_count` é derivado de reservas e não gera registros artificiais por slot.

Os intervalos planejados usam a convenção semiaberta `[início, fim)`. Eles não podem sobrepor reserva confirmada, outra sessão planejada nem ultrapassar uma única janela do calendário operacional. Intervalos adjacentes são válidos.

Check-in antecipado não é permitido. Uma reserva aceita entrada desde `starts_at` até três minutos depois, sem deslocar seu término planejado. A saída pode ocorrer até três minutos depois de `planned_ends_at`. Essa tolerância é exclusivamente operacional: uma sessão planejada até 09h pode permanecer fisicamente até 09h03 mesmo quando a próxima reserva começa às 09h.

Não existe extensão de sessão nesta etapa. Trocas de computador verificam todo o intervalo planejado restante e são proibidas depois de `planned_ends_at`.

Sessões são encerradas logicamente em `exit_deadline_at`, com a alocação marcada como `TIME_LIMIT_REACHED`. Reservas confirmadas são canceladas administrativamente quando o instante corrente ultrapassa `check_in_deadline_at` (ver ADR 0021). A reconciliação ocorre antes de entradas e trocas no computador e por comando periódico executável a cada minuto.

## Alternativas consideradas

- manter ocupação sem término e bloquear apenas o instante atual;
- persistir um registro para cada slot selecionado;
- permitir extensão durante a sessão;
- fazer a tolerância deslocar conflitos e o término planejado;
- manter duração e tolerância em `BookingPolicy`.

## Consequências positivas

- reservas e sessões disputam intervalos completos e determinísticos;
- uma sessão ativa deixa de ocupar indefinidamente os slots futuros;
- fechamento e próxima reserva limitam a duração antes da entrada;
- horário planejado e horário real permanecem distinguíveis em auditoria e relatórios;
- atrasos de até três minutos não alteram o compromisso planejado;
- reconciliação oportunista reduz a dependência do comando periódico.

## Consequências negativas e riscos

- clientes precisam enviar `slot_count` para reserva; uso imediato segue a ADR 0025;
- sessões e reservas ganham campos obrigatórios e exigem migração em fases;
- a implantação deve ocorrer sem sessões legadas ativas;
- durante a tolerância pode existir sobreposição física deliberada com reserva ou fechamento;
- não há extensão de duração, portanto o usuário precisa decidir antes da entrada.
