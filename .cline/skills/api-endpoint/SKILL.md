---
name: api-endpoint
description: Cria ou altera endpoints Django REST Framework da API v1 deste projeto. Use ao trabalhar com serializers, views, routers, URLs, erros, filtros, permissões simuladas ou documentação OpenAPI.
---

# Endpoint DRF

## 1. Contrato antes do código

1. Leia `AGENTS.md`.
2. Consulte `docs/architecture/04-api-v1.md` e as regras funcionais relacionadas.
3. Defina método, rota, parâmetros, corpo, resposta, erros e perfil autorizado.
4. Verifique se um endpoint existente já cobre o caso.

Todos os endpoints públicos desta etapa devem permanecer sob `/api/v1/`.

## 2. Separação de responsabilidades

- Serializer valida formato e dados de entrada.
- Serviço de domínio executa regra de negócio e alterações transacionais.
- Selector executa consultas complexas ou projeções.
- View coordena request, serviço e response.
- Não duplique a mesma regra em serializer, view e model.

A autorização é simulada no MVP. Não adicionar senha, JWT, OAuth, SSO ou autenticação institucional sem ADR.

## 3. Integridade

- Use transação em operações com múltiplas escritas.
- Trate conflitos de reserva, sessão ou alocação de forma explícita.
- Não confie em status efetivo enviado pelo cliente.
- Calcule `OCCUPIED` e `RESERVED` no servidor.
- Retorne erros de domínio com código estável e mensagem compreensível.
- Não exponha dados além do necessário para o perfil simulado.

## 4. OpenAPI

Documente:

- parâmetros;
- schemas de entrada e saída;
- códigos HTTP;
- exemplos de erro relevantes;
- descrição da regra de negócio quando não for óbvia.

Atualize `docs/architecture/04-api-v1.md` quando o contrato mudar.

## 5. Testes

Cubra:

- sucesso;
- dados ausentes ou inválidos;
- perfil sem autorização;
- recurso inexistente;
- conflito de domínio;
- efeito persistido;
- ausência de efeitos parciais após falha.

## 6. Conclusão

Execute as verificações disponíveis e apresente rota, contrato, testes e documentação alterada. Não declare sucesso sem informar os comandos executados e seus resultados.
