# Autorização simulada

## Objetivo

Permitir que o MVP demonstre diferentes perfis sem implementar autenticação real.

## Fluxo

1. o visitante abre a aplicação;
2. escolhe um perfil de teste;
3. o sistema armazena o perfil na sessão Django ou em contexto temporário equivalente;
4. menus, páginas e endpoints aplicam políticas compatíveis com o perfil escolhido;
5. o usuário pode trocar de perfil para testar outro fluxo.

## Perfis

```text
ROOM_USER
INTERN
LIBRARY_SUPERVISOR
SYSTEM_ADMIN
```

## Política sugerida

- `ROOM_USER`: operações próprias de consulta, reserva, sessão e ocorrência;
- `INTERN`: acompanhamento operacional, correções, ocorrências e relatórios operacionais;
- `LIBRARY_SUPERVISOR`: funções do Estagiário mais configurações e relatórios gerenciais;
- `SYSTEM_ADMIN`: reservado para telas administrativas e evolução futura.

## Implementação sugerida

- manter o valor em `request.session["demo_profile"]`;
- criar uma pequena camada `DemoProfilePermission` no DRF;
- criar decorators ou mixins equivalentes para views de templates;
- expor endpoint para consultar e alterar o perfil;
- usar dados fictícios associados a referências estáveis de demonstração.

## Restrições

- não criar formulário de senha;
- não criar tokens JWT;
- não criar usuário real apenas para simular perfil;
- não usar o perfil selecionado como prova de identidade;
- não permitir dados pessoais reais nesse modo;
- não publicar o MVP aberto na internet como sistema de produção.

## Transição futura

A autenticação real substituirá a escolha de perfil. Os perfis conceituais poderão virar grupos e permissões Django. A migração deve incluir:

1. modelo de usuário decidido antes das migrations de produção;
2. login e logout reais;
3. grupos e permissões;
4. revisão dos endpoints;
5. testes de autorização;
6. remoção do modo de demonstração em produção;
7. ADR específico para o método de autenticação.

## Critério de aceitação

A seleção de perfil deve ser claramente identificada na interface como simulação. Uma faixa ou aviso persistente deve informar que o ambiente não possui autenticação real.
