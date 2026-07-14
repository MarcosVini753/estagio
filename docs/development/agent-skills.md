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

Também foi adicionada ao `AGENTS.md` uma versão resumida da escada de decisão Ponytail, permitindo que agentes que leem esse padrão, como Codex e Cline, recebam as mesmas diretrizes básicas.

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

Exemplo:

```text
Use /django-feature-development para implementar a consulta de disponibilidade.
Antes de editar, leia AGENTS.md e apresente o plano.
```

## Ativação no Codex do VS Code

O Codex lê `AGENTS.md` na raiz do projeto. Portanto, ao abrir este repositório, as regras funcionais, arquiteturais e a versão adaptada do princípio Ponytail já ficam disponíveis.

As skills em `.cline/skills/` pertencem ao Cline e não devem ser presumidas como comandos do Codex. No Codex, peça o workflow diretamente e cite a seção relevante do `AGENTS.md`.

Exemplo:

```text
Siga AGENTS.md. Trabalhe como no workflow django-model-and-migration:
primeiro apresente o plano, depois crie model, migration, constraints e testes.
```

## Plugin Ponytail completo no Codex CLI

A instalação do plugin completo é feita no terminal da máquina, não por commit no repositório:

```bash
codex plugin marketplace add DietrichGebert/ponytail
codex plugin add ponytail@ponytail
```

Depois:

1. execute `codex`;
2. abra `/hooks`;
3. revise os dois hooks apresentados antes de confiar neles;
4. inicie uma nova conversa.

O plugin usa pequenos hooks em Node.js. Verifique:

```bash
node --version
```

No Codex com suporte a skills, os comandos Ponytail são invocados com `@`, por exemplo:

```text
@ponytail-review
```

A instalação do plugin é opcional neste projeto, porque o `AGENTS.md` já contém a diretriz principal. O plugin adiciona níveis e comandos próprios.

## Quando usar cada skill

### `django-feature-development`

Use para uma fatia completa: regra, serviço, endpoint, template, JavaScript e testes.

### `django-model-and-migration`

Use ao criar ou alterar models, enums, constraints, índices e migrations.

### `api-endpoint`

Use ao criar ou alterar endpoints em `/api/v1/`, serializers, erros e OpenAPI.

### `test-first-change`

Use principalmente para bugs e regras críticas. O primeiro artefato deve ser um teste que reproduza o comportamento.

### `code-review`

Use antes de mergear. Verifica correção, domínio, integridade, segurança, migrations, desempenho, testes e documentação.

### `ponytail-review`

Use depois da revisão normal. Procura somente código que pode ser removido, reutilizado ou simplificado. Não substitui revisão de correção.

### `documentation-sync`

Use quando código, regra, endpoint, modelo ou arquitetura mudar. Compara a alteração com `docs/product/`, `docs/architecture/`, ADRs e OpenAPI.

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

Depois da aprovação:

```text
Implemente somente a menor fatia aprovada.
Execute os testes e verificações disponíveis.
Mostre os arquivos alterados e qualquer risco restante.
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

Para atualizar a adaptação Ponytail, compare o arquivo upstream `.clinerules/ponytail.md` com `.clinerules/20-ponytail.md` e incorpore apenas mudanças compatíveis com as regras deste projeto.
