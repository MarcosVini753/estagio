---
name: documentation-sync
description: Verifica e corrige divergências entre código, regras funcionais, arquitetura, ADRs, diagramas, API e protótipos. Use após mudanças de comportamento, modelos, endpoints ou estrutura do projeto.
---

# Sincronização de documentação

## 1. Identificar a mudança

Leia o diff e classifique-o:

- funcional;
- arquitetural;
- contrato de API;
- modelo de dados;
- interface ou protótipo;
- operação, instalação ou testes.

## 2. Comparar fontes de verdade

Verifique, conforme aplicável:

- `docs/product/` para escopo, atores e regras;
- `docs/architecture/` para estrutura corrente;
- `docs/adr/` para decisões e consequências;
- `docs/diagrams/` para fluxos e modelos visuais;
- OpenAPI e `docs/architecture/04-api-v1.md` para endpoints;
- `README.md` para instalação e execução;
- `prototipos/` apenas como referência visual.

## 3. Regras

- Não reescreva documentos sem necessidade.
- Atualize somente trechos afetados.
- Preserve o histórico dos ADRs; decisões substituídas devem receber novo ADR ou marcação explícita.
- A documentação de arquitetura deve descrever o estado atual, não apenas a intenção inicial.
- Não faça o protótipo prevalecer sobre produto, arquitetura ou ADRs.
- Remova referências obsoletas que possam induzir agentes a implementar comportamento fora do escopo.

## 4. Checklist do projeto

Confirme que nenhuma documentação volta a afirmar:

- existência de fila de espera;
- ator operacional chamado Servidor da Biblioteca;
- autenticação real no MVP;
- persistência de `OCCUPIED` ou `RESERVED`;
- relatório como lançamento independente;
- troca de computador como nova sessão.

## 5. Resultado

Apresente uma matriz curta:

```text
Mudança | Documento afetado | Situação | Ação
```

Depois aplique apenas as correções necessárias e informe os arquivos atualizados.
