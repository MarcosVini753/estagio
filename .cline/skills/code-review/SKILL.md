---
name: code-review
description: Revisa diffs, commits ou pull requests deste projeto com foco em correção, domínio, segurança, integridade de dados, desempenho e manutenção. Use antes de mergear ou quando o usuário pedir revisão de código.
---

# Revisão de código

Não altere arquivos durante a revisão, salvo solicitação explícita. Leia `AGENTS.md`, os documentos relacionados e o diff completo antes de concluir.

## Ordem de análise

1. Correção funcional e aderência às regras do produto.
2. Integridade de dados, transações, constraints e concorrência.
3. Autorização simulada, exposição de dados e limites de confiança.
4. Compatibilidade da API e OpenAPI.
5. Migrations e impacto em dados existentes.
6. Consultas ineficientes, N+1 e processamento desnecessário.
7. Testes ausentes, frágeis ou que não verificam os efeitos corretos.
8. Documentação ou ADRs desatualizados.
9. Duplicação, complexidade e sobre-engenharia.

## Regras específicas do domínio

Confirme que:

- fila de espera não foi introduzida;
- reserva é somente para amanhã;
- hoje é consulta e uso imediato;
- `OCCUPIED` e `RESERVED` continuam calculados;
- troca de computador cria nova alocação, não nova sessão;
- relatórios continuam projeções;
- autenticação real não foi adicionada sem ADR.

## Formato dos achados

Ordene por gravidade:

- `BLOQUEADOR`: perda de dados, falha de segurança, regra central quebrada ou migration destrutiva.
- `ALTO`: comportamento incorreto relevante, concorrência, incompatibilidade de API ou ausência de teste crítico.
- `MÉDIO`: manutenção difícil, consulta ineficiente ou documentação inconsistente.
- `BAIXO`: simplificação ou melhoria localizada sem risco imediato.

Para cada achado, informe:

```text
[GRAVIDADE] caminho:linha — problema objetivo
Impacto: consequência concreta
Correção: mudança mínima recomendada
```

Não liste preferências pessoais como defeitos. Não elogie genericamente. Se não houver achados, diga que a alteração está pronta para merge e mencione apenas riscos não verificáveis, caso existam.
