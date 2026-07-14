# ADR 0005: Adotar autorização simulada no MVP

## Status

Aceita

## Contexto

A primeira versão será usada para validar fluxos e interfaces. Implementar autenticação real agora aumentaria o escopo sem ser necessário para a demonstração inicial.

## Decisão

Exibir uma tela para seleção do perfil de teste e armazenar o perfil escolhido em contexto temporário, preferencialmente na sessão Django. O perfil controla menus e operações simuladas.

## Alternativas consideradas

- autenticação por usuário e senha;
- JWT;
- integração institucional;
- ausência completa de diferenciação entre perfis.

## Consequências positivas

- valida rapidamente os fluxos de cada ator;
- reduz o escopo inicial;
- preserva a arquitetura de autorização por papéis.

## Consequências negativas e riscos

- não existe segurança real;
- o sistema não pode tratar o perfil como identidade;
- dados reais não devem ser utilizados;
- antes de produção será necessário novo ADR e revisão integral de autorização.
