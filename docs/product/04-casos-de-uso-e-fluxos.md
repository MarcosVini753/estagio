# Casos de uso e fluxos

Este documento funciona como índice funcional. Os diagramas completos permanecem em `docs/diagrams/`.

## Usuário da Sala

Casos de uso principais:

- consultar computadores disponíveis para hoje ou amanhã;
- `UC-USR-Consultar funcionamento`: consultar estado, origem e janelas da sala;
- `UC-USR-Visualizar aviso`: visualizar avisos internos ativos;
- consultar horários disponíveis;
- selecionar início e quantidade de slots consecutivos;
- confirmar reserva com duração solicitada (hoje ou amanhã);
- registrar entrada imediata escolhendo duração ou usar integralmente uma reserva;
- registrar saída;
- trocar de computador durante sessão ativa;
- informar problema.

Fluxos críticos:

1. consulta e reserva;
2. entrada imediata hoje;
3. entrada vinculada a reserva;
4. troca de computador;
5. saída;
6. comunicação de problema.

Na reserva, o usuário seleciona um início alinhado e uma quantidade positiva de slots consecutivos. Na entrada imediata, escolhe a duração antes de confirmar. O sistema apresenta o fim planejado e o prazo de saída. Entrada com reserva só ocorre entre o início e três minutos depois; a troca considera todo o intervalo restante e não ocorre durante a tolerância.

## Monitor da Sala

Casos de uso principais:

- consultar sessões ativas;
- consultar calendário operacional e avisos;
- consultar computadores disponíveis, ocupados, reservados, em manutenção ou inativos;
- alterar estado operacional;
- registrar e consultar ocorrências;
- consultar histórico;
- corrigir registro de uso;
- gerar e exportar relatório operacional.

Fluxos críticos:

1. acompanhamento da sala;
2. alteração de estado operacional;
3. correção auditada de sessão;
4. geração de relatório operacional.

## Supervisor da Biblioteca

Possui **todos** os casos de uso e fluxos do Monitor da Sala, além dos seguintes casos de uso adicionais:

- cadastrar computadores;
- configurar turnos analíticos;
- `UC-SUP-Configurar horário semanal`: cadastrar ou versionar os sete dias do calendário regular;
- `UC-SUP-Configurar horário temporário`: definir início, fim e sete dias de um recesso;
- `UC-SUP-Registrar fechamento excepcional`: fechar ou definir horário especial para uma data;
- `UC-SUP-Visualizar reservas afetadas`: revisar conflitos antes de aplicar a mudança;
- `UC-SUP-Publicar aviso`: publicar ou desativar uma comunicação interna;
- configurar parâmetros de relatório;
- analisar uso por período, turno, curso/setor e computador;
- identificar maior movimento e demanda;
- acompanhar taxa de ocupação;
- gerar relatórios consolidados.

## Administrador do Sistema

O papel existe na arquitetura, mas seus casos de uso detalhados serão documentados em etapa futura.

## Ajustes em relação aos artefatos anteriores

- fila de espera foi removida do escopo;
- estados ocupado e reservado são calculados, não persistidos;
- a tela inicial de escolha de perfil substitui autenticação real no MVP;
- calendário operacional e turnos foram separados para impedir que classificação analítica altere a abertura da sala.
- intervalos planejados foram separados dos horários reais para impedir sessões sem limite e preservar a tolerância operacional de três minutos.

## Rastreabilidade

Ao implementar uma operação, o agente deve relacionar:

- regra funcional em `03-regras-de-negocio.md`;
- modelo em `architecture/02-modelo-de-dominio.md`;
- endpoint em `architecture/04-api.md`;
- diagrama UML correspondente;
- testes unitários e de integração.
