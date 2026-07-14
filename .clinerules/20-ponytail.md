---
paths:
  - "backend/**"
  - "prototipos/**"
  - "**/*.py"
  - "**/*.js"
  - "**/*.html"
  - "**/*.css"
  - "pyproject.toml"
  - "compose.y*ml"
  - "Makefile"
---

# Ponytail — implementação mínima e correta

Adaptação para este projeto das regras do projeto [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail), distribuído sob licença MIT.

As regras de `AGENTS.md`, os documentos de produto, a arquitetura e os ADRs sempre prevalecem. Minimalismo não autoriza remover validação, integridade, segurança, acessibilidade, auditoria, migrations ou testes exigidos pelo projeto.

## Escada de decisão

Antes de escrever código, depois de compreender o fluxo afetado, pare no primeiro nível que resolver corretamente o problema:

1. A alteração realmente precisa existir?
2. O repositório já possui implementação, helper ou padrão reutilizável?
3. Python, Django, DRF ou PostgreSQL já oferecem o recurso?
4. HTML, CSS ou o navegador já oferecem o comportamento nativamente?
5. Uma dependência já instalada resolve o problema sem nova complexidade?
6. A solução pode ser expressa de forma direta e pequena?
7. Somente então escreva o mínimo de código novo necessário.

## Regras

- Leia a tarefa, os documentos relevantes e o fluxo completo antes de alterar arquivos.
- Corrija a causa raiz, não apenas o sintoma apresentado.
- Não crie abstrações especulativas, interfaces com uma implementação, factories sem necessidade ou configuração para valores fixos.
- Não adicione dependência quando Python, Django, DRF, PostgreSQL ou a plataforma já resolverem o problema adequadamente.
- Reutilize padrões existentes antes de introduzir uma segunda forma de fazer a mesma coisa.
- Prefira constraints do banco para invariantes persistentes e serviços de domínio para operações transacionais.
- Prefira código simples e explícito a código genérico ou metaprogramação difícil de revisar.
- O menor diff correto vence; o menor diff no lugar errado é outro defeito.
- Não reduza testes abaixo do exigido por `AGENTS.md` e pela documentação de arquitetura.
- Não use minimalismo para omitir tratamento de erros que possa causar perda ou corrupção de dados.
- Quando uma simplificação possuir limite conhecido, registre-o de forma objetiva no código ou na documentação, indicando quando deverá ser revista.
