---
name: ponytail-review
description: Revisa o diff procurando somente sobre-engenharia, código desnecessário, dependências evitáveis, abstrações especulativas e duplicação. Use com /ponytail-review após a revisão normal de correção.
license: MIT
---

# Ponytail Review

Adaptação para Cline da skill `ponytail-review` do projeto [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail), distribuído sob licença MIT.

Esta revisão trata apenas de complexidade. Para correção, segurança, integridade e domínio, use primeiro `/code-review`.

## Processo

Leia o diff e o código relacionado. Para cada item, determine se ele pode ser:

- removido sem perda de comportamento;
- substituído por Python, Django, DRF, PostgreSQL ou recurso nativo da plataforma;
- substituído por algo já existente no repositório;
- adiado por ser flexibilidade especulativa;
- reduzido mantendo clareza e correção.

Não marque como excesso:

- validação em limites de confiança;
- constraints e transações necessárias;
- tratamento de erro que evita perda de dados;
- segurança e acessibilidade;
- testes exigidos pelas regras do projeto;
- auditoria requerida pela arquitetura.

## Formato

Uma linha por achado:

```text
arquivo:linha — TAG: o que remover ou reduzir. Substituição mínima.
```

Tags:

- `delete`: código morto ou funcionalidade especulativa;
- `reuse`: implementação que já existe no repositório;
- `stdlib`: código manual substituível pela biblioteca padrão;
- `framework`: código substituível por Django, DRF ou PostgreSQL;
- `native`: dependência ou JavaScript substituível por HTML, CSS ou navegador;
- `yagni`: abstração sem necessidade atual;
- `shrink`: mesma regra com implementação menor e igualmente clara.

Termine com:

```text
redução estimada: N linhas
```

Se não houver nada relevante, responda apenas: `Já está enxuto.`

Não aplique correções sem solicitação explícita.
