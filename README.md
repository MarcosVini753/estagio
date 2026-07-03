# Sistema de Controle de Uso da Sala de Informática da Biblioteca da UFAC

Repositório com documentação, diagramas UML e protótipo navegável para o sistema web de controle de uso da Sala de Informática da Biblioteca da UFAC.

## Estrutura

- `docs/contexto.txt`: contexto geral do sistema, atores, regras e entidades recomendadas.
- `docs/casos-de-uso.md`: descrições textuais dos casos de uso.
- `docs/diagrams/casos-de-uso/`: diagramas de casos de uso em PlantUML.
- `docs/diagrams/atividades/`: diagramas de atividades dos principais fluxos.
- `prototipos/`: protótipo navegável em HTML, CSS e JavaScript puros.

## Como executar o protótipo

Abra o arquivo `prototipos/index.html` no navegador.

## Diagramas

Os diagramas estão em arquivos `.puml` e podem ser abertos em qualquer ferramenta compatível com PlantUML.

Índice dos diagramas: [`docs/diagrams/README.md`](docs/diagrams/README.md).

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

### Servidor da Biblioteca
- Consultar sessões ativas.
- Acompanhar computadores disponíveis, ocupados e indisponíveis.
- Alterar status operacional de computadores.
- Corrigir registros de uso.
- Gerar e exportar relatórios operacionais.

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
