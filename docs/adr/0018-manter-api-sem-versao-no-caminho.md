# ADR 0018: Manter API sem versão no caminho

## Status

Aceita

## Contexto

O prefixo `/api/v1/` aumentava o tamanho e a complexidade das requisições sem existir consumidor externo, versão paralela ou necessidade concreta de compatibilidade entre contratos incompatíveis. Manter infraestrutura de versionamento antecipadamente contrariava o objetivo de implementação mínima do MVP.

## Decisão

Expor os endpoints sob `/api/`, sem segmento de versão no caminho e sem alias para `/api/v1/`. O health check deixa de anunciar uma versão da API. A versão obrigatória do documento OpenAPI continua identificando apenas o artefato gerado.

Esta decisão substitui a ADR 0006 e somente os trechos sobre versionamento da API nas ADRs 0001 e 0004.

## Alternativas consideradas

- manter `/api/v1/`;
- aceitar simultaneamente `/api/` e `/api/v1/`;
- transportar a versão por header ou parâmetro de query.

## Consequências positivas

- URLs menores e mais simples;
- um único contrato e uma única árvore de rotas;
- ausência de infraestrutura sem uso real no MVP.

## Consequências negativas e riscos

- consumidores do caminho antigo precisam migrar diretamente para `/api/`;
- uma futura mudança incompatível exige migração planejada e nova decisão arquitetural.
