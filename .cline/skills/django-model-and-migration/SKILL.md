---
name: django-model-and-migration
description: Planeja e revisa alterações em models e migrations Django. Use ao criar entidades, campos, constraints, índices, enums, migrations de dados ou mudanças de esquema PostgreSQL.
---

# Models e migrations Django

## 1. Antes da alteração

1. Leia `AGENTS.md`.
2. Consulte `docs/architecture/02-modelo-de-dominio.md`, o ERD e ADRs relacionados.
3. Inspecione models, migrations e dados já existentes.
4. Identifique invariantes, cardinalidades, histórico necessário e impacto em relatórios.

Confirme especialmente:

- se o dado deve ser persistido ou calculado;
- se `null`, valor padrão e exclusão são semanticamente corretos;
- se a mudança exige histórico;
- se existe risco de sobreposição ou concorrência;
- se a migration precisa preservar dados existentes.

## 2. Modelagem

- Não persistir `OCCUPIED` ou `RESERVED` como estado operacional de computador.
- Manter sessão de uso separada de alocação de computador.
- Preferir `TextChoices` para enums estáveis.
- Usar `CheckConstraint`, `UniqueConstraint`, índices e, quando necessário, recursos PostgreSQL para proteger invariantes.
- Evitar campos duplicados que representem a mesma verdade.
- Definir `related_name` somente quando trouxer clareza real.
- Não criar modelo de relatório para dados que devem ser projeções.

## 3. Migration

- Gere migrations pequenas e revisáveis.
- Leia o arquivo gerado antes de aceitá-lo.
- Separe mudança de esquema de migration de dados quando isso reduzir risco.
- Em campos obrigatórios novos, planeje preenchimento dos registros existentes antes de impor `NOT NULL`.
- Não altere migrations já aplicadas em ambientes compartilhados; crie nova migration.
- Inclua reversão segura em migrations de dados sempre que viável.
- Explique operações destrutivas ou potencialmente demoradas.

## 4. Testes e validações

Teste:

- criação válida;
- violações de constraints;
- regras temporais;
- exclusão e proteção de relacionamentos;
- consultas dependentes do novo esquema;
- migrations de dados relevantes.

Execute, quando disponíveis:

```bash
python manage.py makemigrations --check --dry-run
python manage.py check
python manage.py test
```

Use os comandos oficiais do projeto caso sejam diferentes.

## 5. Saída

Apresente:

- motivo da modelagem;
- migration criada;
- constraints e índices adicionados;
- impacto nos dados existentes;
- comandos executados;
- eventual plano de rollback.
