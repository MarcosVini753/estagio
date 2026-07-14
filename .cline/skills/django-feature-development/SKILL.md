---
name: django-feature-development
description: Implementa funcionalidades completas no monólito Django e DRF deste projeto. Use ao criar ou alterar fluxos de negócio, apps, services, selectors, templates, views, serializers ou integrações entre módulos.
---

# Desenvolvimento de funcionalidade Django

## 1. Compreender antes de editar

1. Leia `AGENTS.md`.
2. Leia os documentos funcionais relacionados em `docs/product/`.
3. Leia os documentos de arquitetura e ADRs relacionados.
4. Inspecione o código existente e localize padrões reutilizáveis.
5. Liste regras de negócio, entradas, saídas, falhas e critérios de aceitação.

Não implemente fila de espera nem autenticação real. Não transforme estados calculados de computador em campos persistidos.

## 2. Planejar a menor fatia vertical

Apresente um plano curto com:

- comportamento entregue;
- módulos e arquivos afetados;
- regras e invariantes;
- testes necessários;
- documentação que poderá precisar de atualização.

Evite scaffolding para funcionalidades futuras. Não crie nova camada se a arquitetura documentada já possui local apropriado.

## 3. Implementar

- Regras transacionais pertencem a serviços de domínio.
- Consultas complexas e projeções pertencem a selectors ou módulos de consulta.
- Views e serializers devem coordenar entrada e saída, não duplicar regras.
- Use `transaction.atomic()` e bloqueios quando houver risco de concorrência.
- Use constraints do banco para invariantes persistentes.
- Preserve a API em `/api/v1/`.
- Mantenha o frontend em Django Templates e JavaScript puro, salvo ADR contrário.

## 4. Testar

Crie testes para:

- caminho principal;
- regras de negócio críticas;
- permissões ou perfil simulado;
- entradas inválidas;
- conflitos e concorrência quando aplicável;
- efeitos persistidos e efeitos que não devem ocorrer.

Não remova, ignore ou enfraqueça testes para fazer a alteração passar.

## 5. Validar e documentar

Execute os comandos de qualidade disponíveis no repositório. Quando existirem, priorize:

```bash
make check
```

ou, na ausência dele, os comandos documentados em `README.md`, `pyproject.toml` e CI.

Atualize:

- `docs/product/` quando o comportamento mudar;
- `docs/architecture/` quando a estrutura corrente mudar;
- ADR quando houver decisão arquitetural relevante;
- OpenAPI e `docs/architecture/04-api-v1.md` quando o contrato da API mudar.

## 6. Relatório final

Informe objetivamente:

- arquivos alterados;
- comportamento implementado;
- testes e verificações executados;
- riscos ou pendências reais.
