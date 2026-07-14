# Regras de negócio

## Datas e horários

- A consulta de disponibilidade aceita somente hoje ou amanhã.
- Para hoje, horários cujo início já passou não podem ser selecionados para novo uso.
- Uso imediato é permitido somente hoje.
- Reserva antecipada é permitida somente para amanhã.
- Datas anteriores ou posteriores a amanhã devem ser rejeitadas.
- Horários devem respeitar o funcionamento da sala e os turnos configurados.

## Computadores

- O estado operacional persistido é apenas `AVAILABLE`, `MAINTENANCE` ou `INACTIVE`.
- `OCCUPIED` é calculado quando existe alocação ativa no instante consultado.
- `RESERVED` é calculado quando existe reserva válida sobreposta ao período consultado.
- `INACTIVE` e `MAINTENANCE` têm precedência sobre estados calculados.
- Computador em manutenção ou inativo não pode receber reserva, entrada ou troca.
- Um computador pode possuir no máximo uma alocação ativa.
- Mudança de estado operacional deve registrar responsável, horário e justificativa quando aplicável.

## Disponibilidade efetiva

Ordem de avaliação:

1. `INACTIVE`;
2. `MAINTENANCE`;
3. `OCCUPIED`;
4. `RESERVED`;
5. `AVAILABLE`.

A disponibilidade sempre depende de data, hora ou intervalo. Não deve existir campo persistido como `statusToday` ou `statusTomorrow` no modelo definitivo.

## Reservas

- Toda reserva pertence a um usuário e computador.
- Toda reserva possui início, fim e estado.
- Reservas novas só podem ser criadas para amanhã.
- Reservas válidas de um mesmo computador não podem se sobrepor.
- O usuário não pode possuir reservas conflitantes.
- Reserva cancelada não bloqueia disponibilidade.
- Ao registrar entrada dentro de uma reserva válida, a sessão pode ser vinculada à reserva.
- Reservas não utilizadas devem poder ser classificadas como `NO_SHOW` por regra configurável futura.

## Sessões

- Um usuário pode possuir no máximo uma sessão ativa.
- A sessão registra entrada e saída reais.
- O registro de entrada cria uma sessão ativa e sua primeira alocação.
- O registro de saída encerra a alocação atual e a sessão.
- A hora de saída não pode ser anterior à hora de entrada.
- O turno principal da visita é calculado a partir do horário de entrada.
- Correções administrativas exigem justificativa e auditoria.

## Alocações e troca de computador

- Uma sessão contém uma ou mais alocações.
- Cada alocação representa o intervalo em que um computador foi usado.
- Trocar de computador encerra a alocação atual e cria outra na mesma sessão.
- O histórico anterior nunca deve ser sobrescrito.
- A troca deve ocorrer atomicamente para impedir que duas pessoas ocupem o mesmo computador.

## Ocorrências

- A ocorrência pode ser associada a computador, sessão e alocação.
- A descrição é obrigatória.
- O usuário informa o problema, mas não altera diretamente o estado operacional.
- Estagiário ou Supervisor pode acompanhar e encerrar a ocorrência.

## Relatórios

- Relatórios são projeções calculadas, não entidades de lançamento manual.
- As fontes são sessões, alocações, reservas, ocorrências, turnos e histórico operacional.
- Uma troca conta como uma sessão e múltiplas alocações.
- O relatório mensal deve reproduzir dias nas linhas, turnos nas colunas e totais no rodapé.
- Total de visitas significa quantidade de sessões, não quantidade de alocações.
- Taxa de ocupação usa tempo alocado dividido pelo tempo operacional disponível.
- Períodos de manutenção e inatividade devem ser excluídos do tempo operacional disponível quando houver histórico suficiente.

## Fora do domínio

- Não existe fila de espera.
- Não existe autenticação real no MVP.
- Não existe integração com sistemas institucionais.
