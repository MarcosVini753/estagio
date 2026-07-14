# Escopo do MVP

## Funcionalidades incluídas

### Seleção de perfil de teste

A aplicação inicial exibe uma tela para escolher o perfil que será simulado:

- Usuário da Sala;
- Estagiário;
- Supervisor da Biblioteca;
- Administrador do Sistema, quando necessário para validar telas administrativas futuras.

A escolha do perfil controla menus e permissões simuladas. Não existe autenticação real no MVP.

### Usuário da Sala

- escolher entre hoje e amanhã;
- consultar computadores e horários disponíveis;
- iniciar uso imediato hoje, desde que o horário não tenha passado;
- reservar computador exclusivamente para amanhã;
- consultar e cancelar suas reservas simuladas;
- registrar entrada;
- visualizar sessão ativa;
- trocar de computador durante a sessão;
- registrar saída;
- informar problema em computador.

### Estagiário

- consultar sessões ativas;
- consultar computadores e seus estados efetivos;
- alterar estado operacional de computador;
- registrar e consultar ocorrências;
- consultar histórico de uso;
- corrigir registro de uso com justificativa;
- gerar e exportar relatórios operacionais.

### Supervisor da Biblioteca

- cadastrar e editar computadores;
- configurar turnos;
- configurar parâmetros de relatório;
- analisar uso por período, turno, curso/setor e computador;
- identificar dias e horários de maior demanda;
- acompanhar taxa de ocupação;
- gerar relatórios diário, semanal, mensal e anual consolidados.

### Administrador do Sistema

O papel existe na arquitetura, mas sua implementação completa não faz parte deste MVP. A estrutura deve permitir evolução futura para:

- contas;
- grupos e permissões;
- parâmetros gerais;
- logs de auditoria.

## Funcionalidades explicitamente excluídas

- fila de espera;
- autenticação real por usuário e senha;
- integração com SSO, LDAP ou conta institucional;
- recuperação de senha;
- notificações por e-mail, SMS ou push;
- aplicação mobile nativa;
- integração com sistemas externos da UFAC;
- microsserviços e processamento assíncrono;
- lançamentos manuais de relatórios.

## Critério de conclusão do MVP

O MVP estará funcional quando for possível simular de ponta a ponta:

1. escolher o perfil Usuário da Sala;
2. consultar hoje e amanhã;
3. iniciar uma sessão hoje ou reservar um horário amanhã;
4. trocar de computador preservando o histórico;
5. encerrar a sessão;
6. visualizar os dados produzidos em relatórios operacionais e consolidados;
7. executar operações do Estagiário e Supervisor de acordo com o perfil selecionado.
