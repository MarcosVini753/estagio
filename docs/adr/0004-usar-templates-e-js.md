# ADR 0004: Usar Django Templates e JavaScript puro

## Status

Substituída pela ADR 0023.

## Contexto

O repositório já possuía um protótipo funcional em HTML, CSS e JavaScript puro. O sistema não exigia uma SPA complexa na primeira versão.

## Decisão original

Usar Django Templates para páginas e JavaScript puro para interações, consumindo a API `/api/` quando necessário.

A referência histórica a um caminho versionado da API deixou de valer com a ADR 0018. A estratégia de frontend desta ADR foi posteriormente refinada e substituída pela ADR 0023.

## Alternativas consideradas

- React;
- Vue;
- frontend totalmente separado;
- páginas Django sem API.

## Consequências positivas observadas

- menor complexidade de build e implantação;
- reaproveitamento visual do protótipo;
- mesma origem para páginas e API;
- evolução progressiva do frontend.

## Limitações que motivaram a substituição

- JavaScript puro sem convenções adicionais tende a crescer de forma pouco estruturada;
- interações simples com o servidor exigiriam código manual repetitivo para requisições e atualização do DOM;
- faltava uma decisão explícita para CSS utilitário, estado local de interface e evolução progressiva para PWA;
- componentes reutilizáveis precisavam de uma estratégia mais clara sem introduzir uma SPA.
