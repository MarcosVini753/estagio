# Glossário

## Usuário da Sala

Aluno, professor ou técnico-administrativo autorizado a utilizar a Sala de Informática.

## Monitor da Sala

Papel operacional responsável por acompanhar a sala, corrigir registros e tratar ocorrências. Não acessa relatórios.

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

Bloqueio antecipado de um computador por uma quantidade de slots consecutivos de 15 minutos. Pode estar confirmada, cancelada ou utilizada e referencia a política vigente em sua criação.

## Política de reserva

Versão temporal das regras de cancelamento e limite de reservas, delimitada por `valid_from` e `valid_until`. Reservas existentes continuam vinculadas à versão originalmente aplicada.

## Sessão de uso

Registro da visita de um usuário. Mantém o intervalo planejado solicitado e, separadamente, os horários reais de entrada e saída.

## Slot

Unidade fixa de 15 minutos usada para compor a duração consecutiva de reservas e a grade de fins planejados do uso imediato.

## Intervalo planejado

Compromisso semiaberto `[início, fim)` usado para validar reservas, sessões, trocas e fechamento. A tolerância operacional não o amplia.

## Prazo de saída

Instante três minutos após o fim planejado. Até ele a saída pode ser registrada; ao atingi-lo a sessão pode ser encerrada logicamente.

## Tolerância operacional

Exceção de três minutos para check-in antecipado ou atrasado e para saída atrasada. Não desloca o intervalo planejado nem participa do cálculo de conflitos futuros.

## Alocação de computador

Intervalo em que determinado computador foi utilizado dentro de uma sessão. Uma troca cria nova alocação, sem criar nova sessão.

## Uso imediato

Início de sessão hoje, em computador disponível, com fim planejado escolhido na grade fixa antes da entrada. O horário real de entrada não é arredondado e o fluxo não cria uma reserva.

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

## Ocorrência

Registro de problema técnico ou operacional associado opcionalmente a computador, sessão e alocação.

## Relatório consolidado

Projeção gerencial diária, mensal ou anual usada pelo Supervisor.

## Perfil de teste

Papel selecionado na tela inicial do MVP para simular autorização. Não representa autenticação ou identidade comprovada.

## MVP

Primeira versão funcional destinada a validar regras, fluxos, interface e persistência com dados fictícios.
