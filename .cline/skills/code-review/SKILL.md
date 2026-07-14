---
name: code-review
description: Revisa diffs, commits ou pull requests deste projeto com foco em correção, domínio, integridade de dados, desempenho e manutenção.
---

# Revisão de código

Leia `AGENTS.md`, os documentos relacionados e o diff completo. Não altere arquivos durante a revisão salvo solicitação explícita.

## Ordem de análise

1. Correção funcional.
2. Integridade, transações, constraints e concorrência.
3. Autorização simulada e exposição de dados.
4. Compatibilidade da API e OpenAPI.
5. Migrations e impacto em dados.
6. Consultas ineficientes.
7. Testes ausentes ou frágeis.
8. Documentação e ADRs.
9. Duplicação e sobre-engenharia.

## Invariantes

Confirme que:

- fila de espera não foi introduzida;
- reservas são limitadas a horários futuros de hoje ou amanhã;
- uso imediato continua restrito a hoje;
- `OCCUPIED` e `RESERVED` são calculados;
- troca cria nova alocação, não nova sessão;
- relatórios continuam projeções;
- autenticação real e Django Admin não foram adicionados sem ADR.

## Gravidade

- `BLOQUEADOR`: perda de dados, segurança, regra central ou migration destrutiva.
- `ALTO`: comportamento relevante incorreto, concorrência ou incompatibilidade.
- `MÉDIO`: manutenção, desempenho ou documentação inconsistente.
- `BAIXO`: simplificação localizada.

Formato:

```text
[GRAVIDADE] caminho:linha — problema
Impacto: consequência concreta
Correção: mudança mínima recomendada
```
