# Atores e permissões

## Visão geral

A primeira versão não possui autenticação real. O usuário escolhe um perfil de teste em uma tela inicial e a aplicação passa a exibir as funcionalidades correspondentes.

Essa autorização é apenas comportamental. Ela não garante identidade, sigilo ou segurança. O MVP deve operar somente com dados fictícios em ambiente local ou controlado.

Ao escolher Usuário da Sala, a demonstração exige referência fictícia, vínculo e unidade institucional. Esses dados distinguem pessoas e agrupamentos analíticos, mas não comprovam identidade.

## Usuário da Sala

Representa aluno, professor ou técnico-administrativo que utiliza os computadores.

Pode:

- consultar disponibilidade de hoje e amanhã;
- consultar o funcionamento da sala e avisos ativos;
- iniciar uso imediato hoje;
- reservar para hoje ou amanhã, em horários válidos;
- consultar e cancelar suas próprias reservas simuladas;
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
- corrigir registros com justificativa;
- consultar histórico de uso;
- gerar e exportar relatórios operacionais.

O Supervisor da Biblioteca herda todas estas capacidades.

## Supervisor da Biblioteca

Representa o papel gerencial.

Pode executar **todas** as ações do Monitor da Sala e, adicionalmente:

- cadastrar computadores;
- configurar turnos analíticos;
- cadastrar e versionar o horário semanal regular;
- criar horário temporário com início e fim para recessos;
- registrar fechamento excepcional ou horário especial;
- visualizar reservas afetadas e confirmar sua invalidação com justificativa;
- publicar e desativar avisos internos;
- configurar parâmetros de relatórios;
- consultar indicadores gerenciais;
- gerar relatórios consolidados.

Nos diagramas separados, as ações herdadas do Monitor da Sala podem ser omitidas para reduzir poluição visual.

## Administrador do Sistema

É o papel de maior privilégio arquitetural.

Responsabilidades futuras:

- administrar contas;
- administrar grupos e permissões;
- configurar parâmetros globais;
- consultar eventos de auditoria;
- realizar manutenção administrativa.

Na autorização simulada atual, o Administrador também pode executar as ações de configuração operacional disponíveis ao Supervisor. Isso não representa autenticação administrativa real.

Seus casos de uso detalhados permanecem fora do escopo documental funcional atual, mas nenhum desenho técnico deve assumir que Supervisor é o maior papel possível.

## Perfis simulados

Sugestão de identificadores internos:

```text
ROOM_USER
INTERN
LIBRARY_SUPERVISOR
SYSTEM_ADMIN
```

A seleção pode ser armazenada temporariamente na sessão Django ou no estado local do frontend. O backend não deve tratar esse valor como prova de identidade.

Para Usuário da Sala, a sessão Django também armazena `demo_user_reference`, `demo_affiliation_type` e `demo_institutional_unit`. Os demais perfis usam apenas referências operacionais fixas.

## Evolução futura

Quando autenticação real for implementada:

- usar o sistema de usuários, grupos e permissões do Django;
- substituir o seletor de perfil por login;
- preservar os mesmos identificadores conceituais de papel quando possível;
- exigir novo ADR para definir o método de autenticação;
- revisar todos os endpoints antes de permitir dados reais.
