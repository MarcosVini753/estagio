# ADR 0006: Versionar API em /api/v1

## Status

Aceita

## Contexto

O frontend será migrado gradualmente do estado simulado para chamadas HTTP. A API precisa evoluir sem quebrar consumidores existentes.

## Decisão

Versionar a API desde o início pelo caminho `/api/v1/`.

## Alternativas consideradas

- API sem versão;
- versão por header;
- versão por parâmetro de query.

## Consequências positivas

- roteamento e documentação explícitos;
- testes organizados por versão;
- possibilidade de manter versões incompatíveis durante migração.

## Consequências negativas e riscos

- endpoints não devem ser criados fora do prefixo;
- mudanças incompatíveis exigem planejamento;
- não se deve criar `/api/v2/` para alterações compatíveis ou meramente aditivas.
