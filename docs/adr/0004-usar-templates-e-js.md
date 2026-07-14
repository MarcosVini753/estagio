# ADR 0004: Usar Django Templates e JavaScript puro

## Status

Aceita

## Contexto

O repositório já possui um protótipo funcional em HTML, CSS e JavaScript puro. O sistema não exige uma SPA complexa na primeira versão.

## Decisão

Usar Django Templates para páginas e JavaScript puro para interações, consumindo a API `/api/v1/` quando necessário.

## Alternativas consideradas

- React;
- Vue;
- frontend totalmente separado;
- páginas Django sem API.

## Consequências positivas

- menor complexidade de build e implantação;
- reaproveitamento visual do protótipo;
- mesma origem para páginas e API;
- evolução progressiva do frontend.

## Consequências negativas e riscos

- o JavaScript deve ser modularizado para evitar um arquivo monolítico;
- estado do servidor não deve ser duplicado no navegador;
- componentes reutilizáveis precisam de convenções claras;
- eventual migração para SPA exigiria reavaliação arquitetural.
