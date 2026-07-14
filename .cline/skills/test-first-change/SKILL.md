---
name: test-first-change
description: Conduz correções de bugs e mudanças de regra começando por um teste reproduzível. Use ao corrigir defeitos, implementar invariantes críticas ou alterar comportamento existente.
---

# Alteração orientada a testes

## 1. Reproduzir

1. Leia `AGENTS.md` e a regra funcional afetada.
2. Localize o fluxo real e todos os chamadores relevantes.
3. Descreva o comportamento atual e o comportamento esperado.
4. Escreva o menor teste que falhe pelo motivo correto.

Para bugs, prefira um teste de regressão que demonstre a causa raiz, não apenas o sintoma da interface.

## 2. Implementar

- Faça a menor mudança correta que torne o teste novo verde.
- Não altere o teste para acomodar uma implementação incorreta.
- Não remova assertions existentes.
- Não use `skip`, `xfail`, exclusões de cobertura ou mocks excessivos para esconder falhas.
- Preserve regras de domínio e transações.

## 3. Refatorar

Somente depois dos testes passarem:

- remova duplicação introduzida;
- melhore nomes;
- reduza complexidade sem alterar comportamento;
- evite abstração sem segundo uso real.

## 4. Verificar

Execute:

1. o teste novo isoladamente;
2. a suíte do módulo afetado;
3. a suíte completa ou o comando de qualidade definido pelo projeto.

Teste cenários de sucesso, falha e ausência de efeitos parciais quando houver escrita em banco.

## 5. Relatório

Informe:

- teste que reproduziu o problema;
- causa raiz encontrada;
- mudança realizada;
- comandos executados;
- resultado final da suíte.
