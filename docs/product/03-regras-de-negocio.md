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
- Exceções passadas são históricas e não podem ser criadas nem alteradas pelos fluxos administrativos; hoje e datas futuras permanecem editáveis.
- Cada calendário configura exatamente os sete dias. Dia aberto tem ao menos uma janela; dia fechado não tem janelas; janelas do mesmo dia não se sobrepõem.
- Reservas, entrada imediata, slots e tempo operacional disponível devem respeitar o calendário aplicável, independentemente dos turnos.
- Cada slot possui duração fixa de 15 minutos. Reservas solicitam uma quantidade inteira positiva de slots consecutivos; uso imediato escolhe o fim planejado na grade fixa.
- Alterações em calendário já iniciado são feitas por nova versão futura. Para emergência no próprio dia, deve ser criada uma exceção pontual.
- Uma alteração não pode sobrescrever retroativamente os horários que explicam sessões e relatórios históricos.
- Antes de aplicar mudança que reduza funcionamento, o Supervisor visualiza as reservas confirmadas afetadas. A aplicação exige confirmação para cancelá-las administrativamente na mesma transação.
- Ponto facultativo é representado como exceção `CLOSED`; o motivo fica em `description` e, quando publicado, no aviso da sala.
- Avisos operacionais ativos são internos e de transmissão geral; não existe confirmação de leitura nem envio externo no MVP.
- Turnos são faixas analíticas para classificar visitas e não definem quando a sala abre.
- Um turno já usado por sessão não pode ter seus horários ou vigência alterados retroativamente.
- A substituição de turno cria uma nova versão futura e encerra a vigência da versão anterior no dia anterior.

## Computadores

- O estado operacional persistido é apenas `AVAILABLE`, `MAINTENANCE` ou `INACTIVE`.
- `OCCUPIED` usa o prazo de saída para o estado atual, o término planejado para disponibilidade futura e os horários reais para histórico.
- `RESERVED` é calculado quando existe reserva válida sobreposta ao período consultado.
- `INACTIVE` e `MAINTENANCE` têm precedência sobre estados calculados.
- Computador em manutenção ou inativo não pode receber reserva, entrada ou troca.
- Um computador pode possuir no máximo uma alocação ativa.
- Mudança de estado operacional deve registrar responsável, horário e justificativa quando aplicável.
- Ao sair de `AVAILABLE` para `MAINTENANCE` ou `INACTIVE`, uma alocação ativa é transferida para computador capaz de atender todo o intervalo restante; sem alternativa, a sessão é encerrada com `COMPUTER_UNAVAILABLE`.
- Reservas confirmadas ainda utilizáveis são realocadas por intervalo quando houver destino válido e canceladas administrativamente quando não houver.
- Sessão, reservas, estado do computador, histórico e auditoria são reconciliados na mesma transação.

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
- Os únicos estados de reserva são `CONFIRMED`, `CANCELLED` e `USED`.
- Reservas válidas de um mesmo computador não podem se sobrepor.
- O usuário não pode possuir reservas conflitantes.
- Reserva cancelada não bloqueia disponibilidade.
- A criação recebe computador, início alinhado à grade de 15 minutos e `slot_count`; o sistema calcula o fim.
- Todo o intervalo `[starts_at, ends_at)` deve caber em uma única janela de funcionamento e não pode sobrepor reserva confirmada nem sessão planejada do computador ou do usuário.
- Intervalos adjacentes são permitidos: uma reserva que termina às 09h não conflita com outra que começa às 09h.
- `check_in_deadline_at` é três minutos após o início e `exit_deadline_at` é três minutos após o fim.
- A entrada vinculada a reserva é aceita de três minutos antes de `starts_at` até `check_in_deadline_at`, inclusive, respeitados o funcionamento da sala e o estado do computador. Ela registra o horário real sem deslocar o início, fim ou prazo planejados.
- Depois de ultrapassado o prazo de check-in, uma reserva confirmada passa a `CANCELLED`, com perfil `SYSTEM_ADMIN` e motivo “Prazo de check-in expirado.”
- Somente o proprietário ou perfil operacional pode cancelar antes do início e do limite da política.
- Cancelamento realizado por perfil operacional em nome de terceiro exige justificativa e auditoria.
- Cada reserva referencia a versão de `BookingPolicy` aplicada em sua criação; mudanças posteriores não alteram retroativamente seu limite de cancelamento.
- Políticas de reserva são versionadas por `valid_from` e `valid_until` e permanecem recuperáveis historicamente.
- Ao registrar entrada dentro de uma reserva válida, a sessão copia integralmente seu intervalo planejado e prazos.

## Sessões

- Um usuário pode possuir no máximo uma sessão ativa.
- A sessão registra entrada e saída reais.
- A sessão registra também início planejado, fim planejado e prazo máximo de saída.
- No uso imediato, o início planejado é a entrada real. A pessoa escolhe `planned_ends_at` na grade global `07:15 + N × 15 minutos`, em marca estritamente posterior à entrada e dentro da mesma janela operacional.
- O intervalo planejado não pode invadir reserva confirmada, outra sessão planejada ou o fechamento.
- A tolerância de saída de três minutos não participa dos conflitos planejados. Ela pode avançar sobre a reserva seguinte ou o fechamento.
- As tolerâncias são operacionais: orientam check-in, saída e reconciliação, mas não são exibidas à pessoa na área do Usuário da Sala.
- O registro de entrada cria uma sessão ativa e sua primeira alocação.
- O registro de saída encerra a alocação atual e a sessão.
- Saída registrada por perfil operacional em nome de terceiro exige justificativa e auditoria.
- A hora de saída não pode ser anterior à hora de entrada.
- O turno principal da visita é calculado a partir do horário de entrada.
- Correções administrativas exigem justificativa e auditoria.
- A saída antecipada é permitida. A sessão vencida tem a saída registrada automaticamente pela reconciliação no prazo de saída, com motivo `TIME_LIMIT_REACHED`.
- Não existe extensão de sessão neste P0.

## Alocações e troca de computador

- Uma sessão contém uma ou mais alocações.
- Cada alocação representa o intervalo em que um computador foi usado.
- Trocar de computador encerra a alocação atual e cria outra na mesma sessão.
- O histórico anterior nunca deve ser sobrescrito.
- A troca deve ocorrer atomicamente para impedir que duas pessoas ocupem o mesmo computador.
- A troca verifica o destino em todo o intervalo entre o instante atual e o fim planejado.
- A troca é rejeitada quando não resta tempo planejado ou quando a sessão está na tolerância de saída.

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
