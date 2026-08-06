# Glossário

## Usuário da Sala

Aluno, professor ou técnico-administrativo autorizado a utilizar a Sala de Informática.

## Monitor da Sala

Papel operacional responsável por acompanhar a sala, corrigir registros, tratar ocorrências e gerar relatórios operacionais.

## Supervisor da Biblioteca

Papel gerencial responsável por configurações, indicadores e relatórios consolidados.

## Administrador do Sistema

Papel arquitetural responsável futuramente por contas, permissões, parâmetros e auditoria.

## Computador

Recurso físico da sala. Persiste apenas seu estado operacional.

## Estado operacional

Condição administrativa persistida do computador: `AVAILABLE`, `MAINTENANCE` ou `INACTIVE`.

## Estado efetivo

Situação calculada para um instante ou intervalo: pode resultar em `AVAILABLE`, `MAINTENANCE`, `INACTIVE`, `OCCUPIED` ou `RESERVED`.

## Reserva

Bloqueio antecipado de um computador em intervalo específico. No MVP, pode ser criada para hoje (futuro do dia corrente) ou amanhã.

## Sessão de uso

Registro da visita real de um usuário, iniciado na entrada e encerrado na saída.

## Alocação de computador

Intervalo em que determinado computador foi utilizado dentro de uma sessão. Uma troca cria nova alocação, sem criar nova sessão.

## Uso imediato

Início de sessão hoje, em computador disponível e horário ainda não passado. Não cria reserva para hoje.

## Turno

Faixa de horário configurável usada somente para classificação e consolidação analítica dos registros. Não define abertura da sala.

## Calendário operacional

Configuração versionada que determina, para cada dia da semana, se a sala abre e em quais janelas.

## Horário regular

Calendário semanal permanente usado quando não há exceção nem horário temporário aplicável.

## Horário temporário

Calendário com início e fim, usado para recessos ou períodos equivalentes. Depois do término, o horário regular volta a valer automaticamente.

## Janela de funcionamento

Intervalo contínuo de abertura dentro de um dia. Um dia aberto pode possuir uma ou mais janelas sem sobreposição.

## Exceção de calendário

Fechamento ou horário especial para uma data específica, com precedência sobre horários temporários e regulares.

## Aviso da sala

Comunicação interna de transmissão geral, exibida enquanto ativa e dentro do período de visibilidade configurado.

## Reserva invalidada

Reserva antes confirmada que se tornou incompatível com uma alteração do calendário. Não bloqueia disponibilidade nem permite check-in, mas preserva justificativa e histórico.

## Ocorrência

Registro de problema técnico ou operacional associado opcionalmente a computador, sessão e alocação.

## Relatório operacional

Projeção voltada ao acompanhamento cotidiano pelo Monitor da Sala.

## Relatório consolidado

Projeção gerencial diária, mensal ou anual usada pelo Supervisor.

## Perfil de teste

Papel selecionado na tela inicial do MVP para simular autorização. Não representa autenticação ou identidade comprovada.

## MVP

Primeira versão funcional destinada a validar regras, fluxos, interface e persistência com dados fictícios.
