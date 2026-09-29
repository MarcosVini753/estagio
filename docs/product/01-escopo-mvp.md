# Escopo do MVP

## Acesso por conta

O sistema autentica por CPF ou matrícula e senha. O perfil vem da conta provisionada e não pode ser escolhido na tela de login. Os três perfis operacionais disponíveis são:

- Usuário da Sala;
- Monitor da Sala;
- Supervisor da Biblioteca;
- O Administrador do Sistema não possui conta nesta etapa.

Não há autocadastro. Contas futuras são criadas internamente por comando, com senha informada sem eco no terminal. O seed local/teste cria três contas fictícias para demonstração; não as cria em produção nem redefine contas existentes.

## Usuário da Sala

- escolher hoje ou amanhã;
- consultar o status e as janelas de funcionamento da sala;
- visualizar avisos operacionais ativos antes e depois do login;
- consultar computadores e horários;
- iniciar uso imediato hoje escolhendo a saída planejada na grade de 15 minutos;
- reservar um ou mais slots consecutivos para horário futuro de hoje ou de amanhã;
- consultar e cancelar suas reservas simuladas;
- registrar entrada e saída;
- visualizar sessão ativa;
- trocar de computador preservando histórico;
- visualizar horários reais e fim planejado da sessão;
- informar problema.

## Monitor da Sala

- consultar sessões ativas;
- consultar calendário operacional e avisos;
- consultar computadores e estados efetivos;
- alterar estado operacional;
- registrar e consultar ocorrências registradas por usuários;
- consultar e corrigir histórico com justificativa;

## Supervisor

- herda tudo que é feito por monitor;
- cadastrar e editar computadores;
- configurar turnos analíticos sem alterar o horário de abertura;
- configurar o horário semanal regular e horários temporários de recesso;
- registrar exceções pontuais de fechamento ou horário especial;
- visualizar reservas afetadas e confirmar seu cancelamento auditado;
- publicar e desativar avisos internos;
- configurar parâmetros de relatórios;
- analisar uso por período, turno, curso/setor e computador;
- identificar demanda e taxa de ocupação;
- gerar relatórios diário, mensal e anual.

## Administrador

O papel existe arquiteturalmente, mas contas, grupos, permissões e login reais estão fora deste MVP.

## Excluído

- fila de espera;
- integração institucional/SSO, autocadastro, recuperação ou alteração de senha pela interface;
- Django Admin como interface do MVP;
- SSO, LDAP ou integração institucional;
- notificações externas por e-mail, SMS, push, WhatsApp ou serviço equivalente;
- aplicação mobile nativa;
- microsserviços, filas e tarefas assíncronas;
- lançamentos manuais de relatórios;
- extensão de uma sessão já iniciada;
- relatório semanal, mantido como evolução futura.

## Critério de conclusão

O MVP estará funcional quando permitir autenticar as contas operacionais, consultar hoje e amanhã com explicação do funcionamento da sala, reservar somente intervalos consecutivos dentro do calendário operacional, iniciar uma sessão escolhendo o fim planejado sem invadir reservas ou fechamento, reconciliar prazos operacionais, encerrar sessão, trocar computador pelo intervalo restante, registrar ocorrência, configurar horários regulares ou temporários com impacto auditado, exibir avisos internos e visualizar relatórios derivados dos registros operacionais.
