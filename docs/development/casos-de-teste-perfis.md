# Casos de teste interligados por perfil

Este roteiro valida a continuidade de um mesmo dado entre contas autenticadas de perfis operacionais. Ele complementa testes de regra e testes de tela isolados: cada caso começa com uma ação de uma conta e termina conferindo o efeito após login com outra conta.

Use somente banco descartável e dados fictícios. Antes da execução manual, aplique migrations e execute `seed_demo_data`. Entre com os CPFs de demonstração e a senha `Senha123.` documentados no README; faça logout antes de entrar com a conta de outro papel.

## Convenções

- Usuário da Sala: `ROOM_USER`, conta própria, vínculo `STUDENT` e unidade `Sistemas de Informação`.
- Monitor da Sala: `ROOM_MONITOR`, conta própria.
- Supervisor da Biblioteca: `LIBRARY_SUPERVISOR`, conta própria.
- Administrador do Sistema: papel arquitetural sem conta ou login.
- Registre o ID de cada reserva, sessão ou ocorrência gerado no caso para confirmar que o histórico é preservado, em vez de recriado.

## Casos prioritários

| ID | Cadeia de atores | Cenário e passos | Resultado esperado | Cobertura automatizada |
| --- | --- | --- | --- | --- |
| CT-PERF-01 | Usuário → Monitor → Supervisor → Usuário | O Usuário informa uma ocorrência para um computador. O Monitor a move para `IN_REVIEW`. O Supervisor a resolve com nota. O Usuário consulta seus problemas. | A mesma ocorrência mantém o ID; somente o criador a vê na própria lista; o Monitor e o Supervisor veem e mudam o estado permitido; o Usuário vê `RESOLVED` e a nota de resolução. | Playwright iniciado por `StaticLiveServerTestCase` em `apps.web.tests.test_frontend_e2e`; complementar com teste de view quando a transição mudar. |
| CT-PERF-02 | Usuário → Monitor → Usuário | O Usuário cria uma reserva futura. O Monitor coloca o computador em manutenção com justificativa. O Usuário abre a Agenda novamente. | A reserva é realocada para um destino compatível ou fica `CANCELLED` com perfil, instante e motivo administrativos; nenhuma reserva fica sobre computador indisponível. | Serviços de estado operacional e testes de Monitor; executar manualmente a visão do Usuário. |
| CT-PERF-03 | Usuário → Monitor → Supervisor → Usuário | O Usuário inicia sessão. O Monitor torna o computador atual indisponível. O Supervisor consulta o histórico e o Usuário consulta a sessão atual. | A sessão continua com o mesmo ID quando há destino; surge uma nova alocação e a anterior recebe motivo. Sem destino, a sessão é encerrada corretamente. O relatório/histórico preserva ambas as alocações. | Serviços de estado operacional, constraints e histórico do Monitor. |
| CT-PERF-04 | Supervisor → Usuário → Monitor | O Supervisor cria prévia de fechamento ou horário especial para hoje/futuro, confirma conflitos e publica aviso. O Usuário consulta disponibilidade; o Monitor consulta o contexto operacional. | A prévia lista exatamente as reservas afetadas; sem confirmação não há mudança. Após confirmação, calendário, cancelamentos, auditoria e aviso são atômicos. Usuário e Monitor veem a mesma condição efetiva da sala. | Serviços de calendário, APIs de impacto e telas do Supervisor. |
| CT-PERF-05 | Supervisor → Usuário → Supervisor | O Supervisor altera a política de reserva. O Usuário mantém uma reserva anterior e cria outra. O Supervisor verifica auditoria e vigências. | A reserva anterior referencia a política histórica; a nova usa a versão vigente. O evento `BOOKING_POLICY_UPDATED` guarda perfil, IDs e vigências anterior/resultante. | Serviços de políticas e testes de auditoria. |
| CT-PERF-06 | Usuário ↔ Monitor ↔ Supervisor | Cada conta tenta abrir rotas dos outros papéis e executar uma operação privilegiada. Tentativas de injetar papel no formulário/API ou em chaves `demo_*` também são rejeitadas. | Usuário não acessa Monitor/Supervisor; Monitor não acessa gestão; Supervisor herda a operação; perfil nunca pode ser elevado pelo cliente; não há conta de Administrador. | Proteção das views/API, login e E2E com logout/login entre contas. |
| CT-PERF-07 | Usuário/Monitor ↔ Supervisor | Gere dados históricos, consulte Diário, Mensal, Anual e Indicadores e baixe CSV, XLSX e PDF. Repita a chamada JSON e o download com cada perfil. | Supervisor recebe projeção completa e arquivos sem referências individuais; Usuário e Monitor recebem `403`. Tela e arquivos apresentam os mesmos totais e ressalvas. | `apps.reports.test_reports`, testes de views do Supervisor e Playwright. |

## Roteiro detalhado do ciclo de ocorrência

1. Entre na conta de demonstração **Usuário da Sala** e registre uma ocorrência com uma descrição única.
2. Anote o ID exibido/consultado e confirme que outro Usuário da Sala não recebe a ocorrência na lista ou API própria.
3. Faça logout, entre na conta de **Monitor da Sala**, pesquise a descrição e altere a situação para **Em análise**.
4. Faça logout, entre na conta de **Supervisor da Biblioteca**, abra a área operacional de ocorrências, informe uma nota e altere para **Resolvida**.
5. Faça logout, entre novamente na conta original de **Usuário da Sala** e confira a descrição, a situação **Resolvida** e a nota retornada.
6. Consulte a ocorrência via API, quando aplicável, para conferir que o ID não mudou e que os vínculos com computador, sessão e alocação foram preservados.

Falhas que este caso deve detectar: perda de escopo por referência do Usuário, mudança de estado não autorizada, transição sem nota de resolução, recriação de ocorrência em vez de atualização e páginas que exibem estado desatualizado.

## Critério de aceite

Um fluxo interligado é aprovado somente quando:

1. todos os perfis envolvidos veem o efeito permitido pela sua autorização;
2. perfis sem autorização recebem redirecionamento ou resposta negada, sem mutação parcial;
3. IDs, vínculos históricos e auditoria permanecem consistentes após cada troca de conta;
4. o resultado é confirmado tanto pela interface quanto pelo banco/API quando a regra for transacional.

Ao incluir novo fluxo entre perfis, adicione uma linha nesta matriz, associe-a à regra de produto correspondente e escolha a camada mais barata que prova o comportamento: serviço para invariantes, view para autorização e Playwright para continuidade visual entre sessões de perfil.
