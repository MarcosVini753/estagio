# Atores e permissões

## Visão geral

O login usa CPF ou matrícula e senha, autenticados pelo Django e mantidos em sessão. A conta determina o perfil; o navegador não escolhe nem envia um papel para obter autorização. A senha é armazenada como hash. Não há integração com identidade institucional nem autocadastro, portanto o sistema continua restrito a ambiente local ou controlado com dados fictícios.

Contas possuem nome de exibição, perfil e referência interna estável sem relação com CPF. Cada conta pode ter um CPF, uma matrícula ou ambos; os identificadores são únicos no sistema. A interface não exibe CPF nem referência técnica da própria conta. Usuários da Sala também possuem vínculo e unidade institucional.

O seed de desenvolvimento e testes cria estas credenciais compartilhadas: CPF `999.999.999-91` (Usuário da Sala), `999.999.999-92` (Monitor) e `999.999.999-93` (Supervisor), todas com senha `Senha123.`. Os CPFs de demonstração não passam na validação dos dígitos verificadores e são aceitos somente pelo seed local/teste. O seed não redefine senha nem perfil já alterados e é desativado em produção. Não use essas credenciais com dados reais.

Contas futuras são provisionadas pelo comando interno `create_access_account`; ele solicita a senha sem exibi-la no terminal e não aceita o perfil `SYSTEM_ADMIN`.

## Usuário da Sala

Representa aluno, professor ou técnico-administrativo que utiliza os computadores.

Pode:

- consultar disponibilidade de hoje e amanhã;
- consultar o funcionamento da sala e avisos ativos;
- iniciar uso imediato hoje;
- reservar para hoje ou amanhã, em horários válidos;
- consultar e cancelar suas próprias reservas;
- registrar entrada e saída;
- trocar de computador;
- consultar sua sessão atual;
- informar problema.

Não pode:

- alterar estado operacional de computador;
- corrigir registros históricos;
- consultar dados de outros usuários;
- configurar turnos ou parâmetros;
- alterar calendário operacional, exceções ou avisos;
- acessar relatórios internos.

## Monitor da Sala

Representa o papel operacional da biblioteca.

Pode:

- acompanhar sessões ativas;
- consultar calendário operacional e avisos ativos;
- consultar disponibilidade e ocupação;
- alterar estado operacional de computadores;
- registrar e consultar ocorrências;
- registrar saída administrativa de sessão ativa com justificativa e auditoria;
- corrigir registros com justificativa;
- consultar histórico de uso;

Não pode acessar indicadores, relatórios ou exportações.

O Supervisor da Biblioteca herda todas estas capacidades.

## Supervisor da Biblioteca

Representa o papel gerencial.

Pode executar **todas** as ações do Monitor da Sala e, adicionalmente:

- cadastrar computadores;
- configurar turnos analíticos;
- cadastrar e versionar o horário semanal regular;
- criar horário temporário com início e fim para recessos;
- registrar fechamento excepcional ou horário especial;
- visualizar reservas afetadas e confirmar seu cancelamento com justificativa;
- publicar e desativar avisos internos;
- configurar parâmetros de relatórios;
- consultar indicadores gerenciais por período;
- gerar relatórios diário, mensal e anual;
- exportar as projeções em CSV, XLSX e PDF.

Nos diagramas separados, as ações herdadas do Monitor da Sala podem ser omitidas para reduzir poluição visual.

## Administrador do Sistema

É o papel de maior privilégio arquitetural.

Responsabilidades futuras:

- administrar contas;
- administrar grupos e permissões;
- configurar parâmetros globais;
- consultar eventos de auditoria;
- realizar manutenção administrativa.

O papel permanece conceitual: não há conta `SYSTEM_ADMIN`, formulário de login para esse papel ou credenciais administrativas. Isso não representa uma autorização disponível na aplicação.

Seus casos de uso detalhados permanecem fora do escopo documental funcional atual, mas nenhum desenho técnico deve assumir que Supervisor é o maior papel possível.

## Perfis de acesso

Sugestão de identificadores internos:

```text
ROOM_USER
ROOM_MONITOR
LIBRARY_SUPERVISOR
SYSTEM_ADMIN
```

`AccessAccount` vincula um usuário Django a perfil, nome de exibição, referência interna e, para Usuário da Sala, vínculo e unidade. Os dados operacionais novos usam a referência estável da conta. Chaves `demo_*` de sessões antigas são ignoradas e removidas ao autenticar; elas nunca concedem acesso.

Registros operacionais legados permanecem nos relatórios, mas não são atribuídos às novas contas e não aparecem como registros “meus”: a referência antiga não comprova propriedade. Não há migração automática de titularidade.

## Evolução futura

Evoluções ainda fora do escopo:

- integrar identidade institucional ou SSO;
- criar recuperação e alteração de senha pela interface;
- definir provisionamento e revogação institucional em escala;
- criar conta e interface para Administrador do Sistema;
- revisar todos os controles antes de permitir dados reais.
