# Regras específicas do backend

Estas instruções complementam o `AGENTS.md` da raiz.

- O código Django fica em `backend/`.
- Apps de domínio ficam em `backend/apps/`.
- Configurações ficam em `backend/config/settings/`.
- Regras transacionais devem ficar em serviços de domínio quando forem implementadas.
- Consultas analíticas e projeções devem ficar em selectors ou módulos equivalentes.
- Não implementar autenticação real; usar o contexto de demonstração armazenado na sessão.
- Reservas podem ser criadas para horários futuros de hoje ou para amanhã.
- Não persistir `OCCUPIED` ou `RESERVED` em `Computer`.
- Não criar modelo de relatório agregado.
- Toda alteração de models deve incluir migration e teste.
- Execute `make check`, `make lint` e `make test` antes de concluir.
