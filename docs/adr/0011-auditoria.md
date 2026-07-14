# ADR 0011: Manter auditoria de ações sensíveis

## Status

Aceita

## Contexto

Correções de registros, mudanças de estado operacional e alterações de configuração afetam relatórios e disponibilidade. É necessário saber o que mudou e por quê.

## Decisão

Registrar eventos de auditoria para ações sensíveis, incluindo perfil de teste, entidade, valores anteriores e novos, justificativa e horário.

## Alternativas consideradas

- depender somente dos logs do servidor;
- não registrar histórico no MVP;
- guardar apenas o último responsável no registro alterado.

## Consequências positivas

- facilita diagnóstico e validação;
- mantém histórico de correções;
- prepara o sistema para autenticação real futura.

## Consequências negativas e riscos

- o perfil simulado não comprova identidade;
- valores antigos e novos devem evitar exposição desnecessária;
- auditoria não deve ser usada para reconstruir regras que deveriam estar no domínio.
