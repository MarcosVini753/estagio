# Diagramas

Esta pasta concentra os diagramas PlantUML do Sistema de Controle de Uso da Sala de Informática da Biblioteca da UFAC.

## Casos de uso

- [Usuário da Sala](casos-de-uso/usuario.puml)
- [Estagiário](casos-de-uso/estagiario-biblioteca.puml)
- [Supervisor da Biblioteca](casos-de-uso/supervisor.puml)

O Administrador do Sistema existe arquiteturalmente, mas seus casos de uso detalhados permanecem fora desta etapa.

## Atividades

- [01 — Usuário consulta disponibilidade e agenda computador](atividades/01-usuario-consultar-e-agendar.puml)
- [02 — Usuário registra entrada](atividades/02-usuario-registrar-entrada.puml)
- [03 — Usuário registra saída](atividades/03-usuario-registrar-saida.puml)
- [04 — Usuário troca de computador](atividades/04-usuario-trocar-computador.puml)
- [05 — Usuário informa problema](atividades/05-usuario-informar-problema.puml)
- [06 — Estagiário altera status de computador](atividades/06-estagiario-alterar-status-computador.puml)
- [07 — Estagiário corrige registro](atividades/07-estagiario-corrigir-registro.puml)
- [08 — Estagiário gera e exporta relatório operacional](atividades/08-estagiario-gerar-exportar-relatorio.puml)
- [09 — Supervisor configura o sistema](atividades/09-supervisor-configuracoes.puml)
- [10 — Supervisor analisa indicadores](atividades/10-supervisor-analisar-indicadores.puml)
- [11 — Supervisor gera relatório consolidado](atividades/11-supervisor-gerar-relatorio-consolidado.puml)

## Decisões posteriores aos diagramas

- fila de espera foi removida do escopo;
- reserva antecipada é somente para amanhã;
- hoje permite uso imediato em horários ainda não passados;
- `OCCUPIED` e `RESERVED` são estados calculados;
- autenticação real foi substituída, no MVP, por seleção de perfil de teste.

Ao encontrar divergência, consulte `docs/product/`, `docs/architecture/` e os ADRs.
