# Skills e regras para agentes de código

Este documento explica como usar as regras e skills versionadas no repositório com Cline e Codex dentro do VS Code.

## O que foi instalado no repositório

```text
.clinerules/
└── 20-ponytail.md

.cline/skills/
├── api-endpoint/
├── code-review/
├── django-feature-development/
├── django-model-and-migration/
├── documentation-sync/
├── ponytail-review/
└── test-first-change/
```

O `AGENTS.md` contém uma versão resumida da escada de decisão Ponytail, permitindo que agentes que leem esse padrão recebam as mesmas diretrizes básicas.

## Ponytail neste projeto

O projeto [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) orienta agentes a evitar sobre-engenharia: reutilizar o que já existe, preferir biblioteca padrão, framework e recursos nativos, evitar dependências desnecessárias e produzir o menor diff correto.

A versão deste repositório foi adaptada porque as regras locais exigem testes automatizados, constraints, transações, auditoria e documentação. As regras de produto, arquitetura e `AGENTS.md` sempre prevalecem sobre qualquer tentativa de reduzir código.

## Ativação no Cline

As configurações são locais ao projeto e entram em funcionamento depois de atualizar o repositório:

```bash
git switch main
git pull
```

Depois:

1. abra a raiz do repositório no VS Code;
2. abra o painel do Cline;
3. clique no ícone de regras/skills próximo ao seletor de modelo;
4. na aba **Rules**, confirme que `20-ponytail.md` está habilitada;
5. na aba **Skills**, confirme que as skills em `.cline/skills/` foram detectadas;
6. reinicie a janela do VS Code caso os arquivos não apareçam imediatamente.

As skills podem ser acionadas automaticamente pela descrição ou explicitamente no chat:

```text
/django-feature-development
/django-model-and-migration
/api-endpoint
/test-first-change
/code-review
/ponytail-review
/documentation-sync
```

## Ativação no Codex do VS Code

O Codex lê `AGENTS.md` na raiz do projeto. Portanto, ao abrir este repositório, as regras funcionais, arquiteturais e a versão adaptada do princípio Ponytail já ficam disponíveis.

As skills em `.cline/skills/` pertencem ao Cline e não devem ser presumidas como comandos do Codex. No Codex, peça o workflow diretamente e cite a seção relevante do `AGENTS.md`.

## Quando usar cada skill

- **`django-feature-development`**: fatia completa (regra, serviço, endpoint, template, JavaScript e testes).
- **`django-model-and-migration`**: criar ou alterar models, enums, constraints, índices e migrations.
- **`api-endpoint`**: criar ou alterar endpoints em `/api/`, serializers, erros e OpenAPI.
- **`test-first-change`**: bugs e regras críticas; o primeiro artefato deve ser um teste que reproduza o comportamento.
- **`code-review`**: antes de mergear; verifica correção, domínio, integridade, segurança, migrations, desempenho, testes e documentação.
- **`ponytail-review`**: depois da revisão normal; procura código que pode ser removido, reutilizado ou simplificado.
- **`documentation-sync`**: quando código, regra, endpoint, modelo ou arquitetura mudar; compara com `docs/product/`, `docs/architecture/`, ADRs e OpenAPI.

## Fluxo recomendado por funcionalidade

```text
1. Criar ou escolher uma issue pequena.
2. Usar django-feature-development apenas para planejar.
3. Aprovar o plano.
4. Usar test-first-change quando houver regra crítica ou bug.
5. Usar django-model-and-migration e/ou api-endpoint conforme a tarefa.
6. Executar as verificações do projeto.
7. Executar code-review.
8. Executar ponytail-review.
9. Executar documentation-sync.
10. Revisar o diff manualmente e abrir o pull request.
```

## Prompt inicial recomendado

```text
Leia AGENTS.md e os documentos relacionados antes de editar.
Use a skill adequada à tarefa.
Primeiro apresente um plano curto com arquivos, regras, testes e documentação afetada.
Não implemente até eu aprovar o plano.
```

## Regras de segurança

- Não habilite autoaprovação irrestrita para terminal e escrita de arquivos.
- Leia skills de terceiros antes de instalá-las.
- Revise scripts e hooks antes de confiar neles.
- Nunca permita acesso desnecessário a chaves, tokens ou arquivos fora do projeto.
- Teste plugins novos em branch separada.
- Não aceite alteração de testes apenas para esconder uma falha.

## Atualização das skills

As skills próprias devem evoluir por pull request, como qualquer código do projeto. Ao alterar uma skill:

1. mantenha o nome do diretório igual ao campo `name`;
2. torne a descrição específica para permitir ativação correta;
3. evite duplicar todo o conteúdo de `AGENTS.md`;
4. mantenha cada skill focada em um workflow;
5. teste a ativação automática e por comando `/` no Cline.