# Escopo do MVP

## Seleção de perfil de teste

A aplicação permite escolher:

- Usuário da Sala;
- Estagiário;
- Supervisor da Biblioteca;
- Administrador do Sistema.

A seleção controla menus e autorizações simuladas. Não existe autenticação real.

## Usuário da Sala

- escolher hoje ou amanhã;
- consultar computadores e horários;
- iniciar uso imediato hoje;
- reservar horário futuro de hoje ou de amanhã;
- consultar e cancelar suas reservas simuladas;
- registrar entrada e saída;
- visualizar sessão ativa;
- trocar de computador preservando histórico;
- informar problema.

## Estagiário

- consultar sessões ativas;
- consultar computadores e estados efetivos;
- alterar estado operacional;
- registrar e consultar ocorrências;
- consultar e corrigir histórico com justificativa;
- gerar e exportar relatórios operacionais.

## Supervisor

- cadastrar e editar computadores;
- configurar turnos e parâmetros;
- analisar uso por período, turno, curso/setor e computador;
- identificar demanda e taxa de ocupação;
- gerar relatórios diário, semanal, mensal e anual.

## Administrador

O papel existe arquiteturalmente, mas contas, grupos, permissões e login reais estão fora deste MVP.

## Excluído

- fila de espera;
- autenticação real e recuperação de senha;
- Django Admin como interface do MVP;
- SSO, LDAP ou integração institucional;
- notificações externas;
- aplicação mobile nativa;
- microsserviços, filas e tarefas assíncronas;
- lançamentos manuais de relatórios.

## Critério de conclusão

O MVP estará funcional quando permitir selecionar perfil, consultar hoje e amanhã, reservar horário futuro de hoje ou amanhã, iniciar e encerrar sessão, trocar computador, registrar ocorrência e visualizar relatórios derivados dos registros operacionais.
