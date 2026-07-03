# Protótipo - Sistema de Controle de Uso da Sala de Informática da Biblioteca da UFAC

Protótipo navegável feito apenas com HTML, CSS e JavaScript puros.

## Como executar

Abra o arquivo `index.html` no navegador.

## O que está simulado

### Usuário da Sala
- Consultar computadores disponíveis para o dia atual ou seguinte.
- Alternar entre hoje e amanhã por botões ou deslize lateral na lista.
- Consultar horários disponíveis.
- Selecionar horário disponível.
- Confirmar agendamento para o próximo dia.
- Cancelar agendamento.
- Registrar entrada.
- Registrar saída.
- Trocar de computador durante sessão ativa.
- Informar problema no computador.

### Supervisor da Biblioteca
- Cadastrar computadores.
- Configurar turnos.
- Configurar parâmetros de relatório.
- Analisar uso da sala por período, turno, curso/setor e computador.
- Identificar dias de maior movimento.
- Identificar horários de maior demanda.
- Acompanhar taxa de ocupação dos computadores.
- Gerar relatório diário, semanal, mensal e anual consolidado.

Os dados são persistidos no `localStorage` do navegador. O botão de reiniciar no topo limpa a simulação e volta ao estado inicial.
