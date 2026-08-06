# Regras de negócio

## Datas e horários

- A consulta de disponibilidade aceita somente hoje ou amanhã.
- Para hoje, horários cujo início já passou não podem ser selecionados para novo uso.
- Uso imediato é permitido somente hoje.
- Reserva antecipada pode ser criada para hoje (futuro do dia corrente) ou amanhã.
- Datas anteriores ou posteriores a amanhã devem ser rejeitadas.
- O calendário semanal regular inicial abre de segunda a sexta, das 07h15 às 21h; aos sábados, das 07h15 às 13h; e registra domingo explicitamente como fechado.
- O funcionamento aplicável a uma data segue a precedência: exceção específica, horário temporário, horário semanal regular e, por último, erro de configuração se o calendário regular não existir.
- Um horário temporário deve ter início e fim. Ao terminar sua vigência, o horário regular volta a valer automaticamente.
- Uma exceção pontual pode fechar a sala ou substituir as janelas de uma única data e sempre prevalece sobre horário temporário e regular.
- Cada calendário configura exatamente os sete dias. Dia aberto tem ao menos uma janela; dia fechado não tem janelas; janelas do mesmo dia não se sobrepõem.
- Reservas, entrada imediata, slots e tempo operacional disponível devem respeitar o calendário aplicável, independentemente dos turnos.
- Alterações em calendário já iniciado são feitas por nova versão futura. Para emergência no próprio dia, deve ser criada uma exceção pontual.
- Uma alteração não pode sobrescrever retroativamente os horários que explicam sessões e relatórios históricos.
- Antes de aplicar mudança que reduza funcionamento, o Supervisor visualiza as reservas confirmadas afetadas. A aplicação exige confirmação para invalidá-las na mesma transação.
- Reserva invalidada deixa de bloquear o computador, não pode ser usada no check-in, permanece em “Minhas reservas” com justificativa e é contabilizada separadamente.
- Avisos operacionais ativos são internos e de transmissão geral; não existe confirmação de leitura nem envio externo no MVP.
- Turnos são faixas analíticas para classificar visitas e não definem quando a sala abre.
- Um turno já usado por sessão não pode ter seus horários ou vigência alterados retroativamente.
- A substituição de turno cria uma nova versão futura e encerra a vigência da versão anterior no dia anterior.

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
- Reservas válidas de um mesmo computador não podem se sobrepor.
- O usuário não pode possuir reservas conflitantes.
- Reserva cancelada não bloqueia disponibilidade.
- Reserva invalidada por alteração de calendário não bloqueia disponibilidade.
- A criação recebe somente computador e início de um slot; o sistema calcula o fim.
- Somente o proprietário ou perfil operacional pode cancelar antes do início e do limite da política.
- Cancelamento realizado por perfil operacional em nome de terceiro exige justificativa e auditoria.
- Ao registrar entrada dentro de uma reserva válida, a sessão pode ser vinculada à reserva.
- Reservas não utilizadas devem poder ser classificadas como `NO_SHOW` por regra configurável futura.

## Sessões

- Um usuário pode possuir no máximo uma sessão ativa.
- A sessão registra entrada e saída reais.
- O registro de entrada cria uma sessão ativa e sua primeira alocação.
- O registro de saída encerra a alocação atual e a sessão.
- Saída registrada por perfil operacional em nome de terceiro exige justificativa e auditoria.
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
- Monitor da Sala ou Supervisor pode acompanhar e encerrar a ocorrência.

## Relatórios

- Relatórios são projeções calculadas, não entidades de lançamento manual.
- As fontes são sessões, alocações, reservas, ocorrências, turnos e histórico operacional.
- O calendário operacional efetivo é a fonte dos dias abertos, janelas e tempo operacional disponível; turnos permanecem apenas como dimensão analítica.
- Uma troca conta como uma sessão e múltiplas alocações.
- O relatório mensal deve reproduzir dias nas linhas, turnos nas colunas e totais no rodapé.
- Total de visitas significa quantidade de sessões, não quantidade de alocações.
- Taxa de ocupação usa tempo alocado dividido pelo tempo operacional disponível.
- Domingo regular e demais dias fechados possuem zero tempo operacional; no sábado regular, o denominador termina às 13h.
- Períodos de manutenção e inatividade devem ser excluídos do tempo operacional disponível quando houver histórico suficiente.

## Fora do domínio

- Não existe fila de espera.
- Não existe autenticação real no MVP.
- Não existe integração com sistemas institucionais.
