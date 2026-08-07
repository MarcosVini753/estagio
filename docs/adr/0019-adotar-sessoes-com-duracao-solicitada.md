# ADR 0019: Adotar sessões com duração solicitada

## Status

Aceita. A semântica de `NO_SHOW` foi substituída pela ADR 0021; intervalos planejados e deadlines permanecem vigentes.

## Contexto

Reservas representavam um único slot configurável, enquanto sessões imediatas tinham apenas horários reais de entrada e saída. Uma alocação ativa sem término ocupava todos os horários futuros na projeção de disponibilidade. Como a validação observava somente o instante da entrada ou da troca, uma sessão podia começar pouco antes de uma reserva ou do fechamento sem possuir limite planejado.

O domínio precisa distinguir o compromisso de uso assumido antes da entrada do intervalo real posteriormente registrado. Também precisa tolerar uma saída operacionalmente atrasada sem transformar essa tolerância em disponibilidade planejada.

## Decisão

Adotar o Modelo C, no qual cada reserva ou uso imediato possui uma duração solicitada como quantidade inteira de slots consecutivos. O slot é uma regra fixa de 15 minutos e não uma política alterável pelo Supervisor.

`Reservation` mantém `starts_at` e `ends_at`, recebe `slot_count` na criação e persiste `check_in_deadline_at`, `exit_deadline_at` e `no_show_at`. `UseSession` persiste `planned_starts_at`, `planned_ends_at` e `exit_deadline_at`, além dos horários reais. `slot_count` é derivado do intervalo planejado e não gera registros artificiais por slot.

Os intervalos planejados usam a convenção semiaberta `[início, fim)`. Eles não podem sobrepor reserva confirmada, outra sessão planejada nem ultrapassar uma única janela do calendário operacional. Intervalos adjacentes são válidos.

Check-in antecipado não é permitido. Uma reserva aceita entrada desde `starts_at` até três minutos depois, sem deslocar seu término planejado. A saída pode ocorrer até três minutos depois de `planned_ends_at`. Essa tolerância é exclusivamente operacional: uma sessão planejada até 09h pode permanecer fisicamente até 09h03 mesmo quando a próxima reserva começa às 09h.

Não existe extensão de sessão nesta etapa. Trocas de computador verificam todo o intervalo planejado restante e são proibidas depois de `planned_ends_at`.

Sessões são encerradas logicamente em `exit_deadline_at`, com a alocação marcada como `TIME_LIMIT_REACHED`. Reservas confirmadas tornam-se `NO_SHOW` apenas quando o instante corrente ultrapassa `check_in_deadline_at`. A reconciliação ocorre antes de entradas e trocas no computador e por comando periódico executável a cada minuto.

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

- clientes precisam enviar `slot_count` para reserva e uso imediato;
- sessões e reservas ganham campos obrigatórios e exigem migração em fases;
- a implantação deve ocorrer sem sessões legadas ativas;
- durante a tolerância pode existir sobreposição física deliberada com reserva ou fechamento;
- não há extensão de duração, portanto o usuário precisa decidir antes da entrada.
