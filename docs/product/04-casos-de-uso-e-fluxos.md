# Casos de uso e fluxos

Este documento funciona como índice funcional. Os diagramas completos permanecem em `docs/diagrams/`.

## Usuário da Sala

Casos de uso principais:

- consultar computadores disponíveis para hoje ou amanhã;
- consultar horários disponíveis;
- selecionar horário;
- confirmar reserva para amanhã;
- cancelar reserva;
- registrar entrada;
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

## Estagiário

Casos de uso principais:

- consultar sessões ativas;
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

Casos de uso adicionais:

- cadastrar computadores;
- configurar turnos;
- configurar parâmetros de relatório;
- analisar uso por período, turno, curso/setor e computador;
- identificar maior movimento e demanda;
- acompanhar taxa de ocupação;
- gerar relatórios consolidados.

## Administrador do Sistema

O papel existe na arquitetura, mas seus casos de uso detalhados serão documentados em etapa futura.

## Ajustes em relação aos artefatos anteriores

- referências a Servidor da Biblioteca devem ser interpretadas e substituídas por Estagiário;
- fila de espera foi removida do escopo;
- estados ocupado e reservado são calculados, não persistidos;
- a tela inicial de escolha de perfil substitui autenticação real no MVP;
- reservas são somente para amanhã; hoje permite uso imediato.

## Rastreabilidade

Ao implementar uma operação, o agente deve relacionar:

- regra funcional em `03-regras-de-negocio.md`;
- modelo em `architecture/02-modelo-de-dominio.md`;
- endpoint em `architecture/04-api-v1.md`;
- diagrama UML correspondente;
- testes unitários e de integração.
