# Casos de teste interligados por perfil

Este roteiro valida a continuidade de um mesmo dado entre os perfis simulados do MVP. Ele complementa testes unitários de regra e testes de tela isolados: cada caso começa com uma ação de um ator e termina conferindo o efeito para outro ator.

Use somente banco descartável e referências fictícias. Antes da execução manual, aplique migrations e execute `seed_demo_data`.

## Convenções

- Usuário da Sala: `ROOM_USER`, referência `aluno-teste-001`, vínculo `STUDENT` e unidade `Sistemas de Informação`.
- Monitor da Sala: `ROOM_MONITOR`.
- Supervisor da Biblioteca: `LIBRARY_SUPERVISOR`.
- Administrador do Sistema: `SYSTEM_ADMIN`.
- Registre o ID de cada reserva, sessão ou ocorrência gerado no caso para confirmar que o histórico é preservado, em vez de recriado.

## Casos prioritários

| ID | Cadeia de atores | Cenário e passos | Resultado esperado | Cobertura automatizada |
| --- | --- | --- | --- | --- |
| CT-PERF-01 | Usuário → Monitor → Supervisor → Usuário | O Usuário informa uma ocorrência para um computador. O Monitor a move para `IN_REVIEW`. O Supervisor a resolve com nota. O Usuário consulta seus problemas. | A mesma ocorrência mantém o ID; somente o criador a vê na própria lista; o Monitor e o Supervisor veem e mudam o estado permitido; o Usuário vê `RESOLVED` e a nota de resolução. | Playwright em `scripts/frontend-e2e.mjs`; complementar com teste de view quando a transição mudar. |
| CT-PERF-02 | Usuário → Monitor → Usuário | O Usuário cria uma reserva futura. O Monitor coloca o computador em manutenção com justificativa. O Usuário abre a Agenda novamente. | A reserva é realocada para um destino compatível ou fica `CANCELLED` com perfil, instante e motivo administrativos; nenhuma reserva fica sobre computador indisponível. | Serviços de estado operacional e testes de Monitor; executar manualmente a visão do Usuário. |
| CT-PERF-03 | Usuário → Monitor → Supervisor → Usuário | O Usuário inicia sessão. O Monitor torna o computador atual indisponível. O Supervisor consulta o histórico e o Usuário consulta a sessão atual. | A sessão continua com o mesmo ID quando há destino; surge uma nova alocação e a anterior recebe motivo. Sem destino, a sessão é encerrada corretamente. O relatório/histórico preserva ambas as alocações. | Serviços de estado operacional, constraints e histórico do Monitor. |
| CT-PERF-04 | Supervisor → Usuário → Monitor | O Supervisor cria prévia de fechamento ou horário especial para hoje/futuro, confirma conflitos e publica aviso. O Usuário consulta disponibilidade; o Monitor consulta o contexto operacional. | A prévia lista exatamente as reservas afetadas; sem confirmação não há mudança. Após confirmação, calendário, cancelamentos, auditoria e aviso são atômicos. Usuário e Monitor veem a mesma condição efetiva da sala. | Serviços de calendário, APIs de impacto e telas do Supervisor. |
| CT-PERF-05 | Supervisor → Usuário → Supervisor | O Supervisor altera a política de reserva. O Usuário mantém uma reserva anterior e cria outra. O Supervisor verifica auditoria e vigências. | A reserva anterior referencia a política histórica; a nova usa a versão vigente. O evento `BOOKING_POLICY_UPDATED` guarda perfil, IDs e vigências anterior/resultante. | Serviços de políticas e testes de auditoria. |
| CT-PERF-06 | Usuário ↔ Monitor ↔ Supervisor | Cada perfil tenta abrir as rotas dos demais e executar uma operação privilegiada. O Administrador também é selecionado. | Usuário não acessa Monitor/Supervisor; Monitor não acessa gestão; Supervisor herda a operação; Administrador permanece na tela de interface pendente, sem ganhar uma área web não prevista. | Testes de proteção das views e E2E de seleção de perfis. |

## Roteiro detalhado do ciclo de ocorrência

1. Selecione **Usuário da Sala** com a referência de teste e registre uma ocorrência com uma descrição única.
2. Anote o ID exibido/consultado e confirme que outro Usuário da Sala não recebe a ocorrência na lista ou API própria.
3. Troque para **Monitor da Sala**, pesquise a descrição e altere a situação para **Em análise**.
4. Troque para **Supervisor da Biblioteca**, abra a área operacional de ocorrências, informe uma nota e altere para **Resolvida**.
5. Volte ao mesmo **Usuário da Sala** e confira a descrição, a situação **Resolvida** e a nota retornada.
6. Consulte a ocorrência via API, quando aplicável, para conferir que o ID não mudou e que os vínculos com computador, sessão e alocação foram preservados.

Falhas que este caso deve detectar: perda de escopo por referência do Usuário, mudança de estado não autorizada, transição sem nota de resolução, recriação de ocorrência em vez de atualização e páginas que exibem estado desatualizado.

## Critério de aceite

Um fluxo interligado é aprovado somente quando:

1. todos os perfis envolvidos veem o efeito permitido pela sua autorização;
2. perfis sem autorização recebem redirecionamento ou resposta negada, sem mutação parcial;
3. IDs, vínculos históricos e auditoria permanecem consistentes após cada troca de perfil;
4. o resultado é confirmado tanto pela interface quanto pelo banco/API quando a regra for transacional.

Ao incluir novo fluxo entre perfis, adicione uma linha nesta matriz, associe-a à regra de produto correspondente e escolha a camada mais barata que prova o comportamento: serviço para invariantes, view para autorização e Playwright para continuidade visual entre sessões de perfil.
