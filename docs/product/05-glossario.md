# Glossário

## Usuário da Sala

Aluno, professor ou técnico-administrativo autorizado a utilizar a Sala de Informática.

## Estagiário

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

Faixa de horário configurável usada para classificação e consolidação dos registros.

## Ocorrência

Registro de problema técnico ou operacional associado opcionalmente a computador, sessão e alocação.

## Relatório operacional

Projeção voltada ao acompanhamento cotidiano pelo Estagiário.

## Relatório consolidado

Projeção gerencial diária, semanal, mensal ou anual usada pelo Supervisor.

## Perfil de teste

Papel selecionado na tela inicial do MVP para simular autorização. Não representa autenticação ou identidade comprovada.

## MVP

Primeira versão funcional destinada a validar regras, fluxos, interface e persistência com dados fictícios.
