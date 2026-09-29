# Autenticação e autorização

## Objetivo e limites

O MVP identifica a conta por CPF ou matrícula e senha e usa a sessão padrão do
Django. Isso substitui a antiga seleção pública de perfil. O perfil autorizado
é persistido em `AccessAccount`; o navegador não pode escolhê-lo nem alterar a
identidade por payload ou por chaves de sessão antigas.

Este é um login local do próprio MVP, não uma integração com a UFAC, SSO ou
diretório institucional. O sistema continua restrito a ambiente local ou
controlado, com dados fictícios. As credenciais compartilhadas do seed nunca
devem ser usadas com dados reais.

## Modelo de conta

- `django.contrib.auth.User` guarda a senha usando o hash configurado pelo
  Django e informa se a conta está ativa;
- `AccessAccount` liga um usuário a perfil, nome de exibição e referência
  operacional opaca; Usuário da Sala também possui vínculo e unidade;
- `LoginIdentifier` guarda CPF e/ou matrícula normalizados, únicos no sistema;
- uma conta pode ter no máximo um CPF e uma matrícula;
- `SYSTEM_ADMIN` é papel arquitetural, sem conta nem entrada de login.

A referência interna não é derivada de CPF ou matrícula. Novas reservas,
sessões e ocorrências usam essa referência. Dados anteriores permanecem nos
relatórios, mas não são atribuídos automaticamente e não aparecem nas listas
“meus”: as referências históricas não comprovam titularidade.

## Fluxo web

1. a pessoa informa CPF ou matrícula e senha na página inicial;
2. o backend normaliza o identificador e autentica pelo backend do Django;
3. contas inativas ou credenciais inválidas recebem a mesma mensagem genérica;
4. o perfil persistido define a área inicial e autorizações;
5. a sessão expira ao fechar o navegador, e o botão **Sair** encerra a sessão
   imediatamente por `POST`.

Não há seleção de perfil, autocadastro ou recuperação de senha pela interface.
Contas adicionais são provisionadas por `create_access_account`; a senha é
solicitada interativamente sem eco no terminal.

## Fluxo API

```text
POST /api/auth/login/
POST /api/auth/logout/
GET  /api/auth/me/
```

Login requer CSRF mesmo para visitante anônimo. Depois, as requisições usam o
cookie de sessão e `SessionAuthentication`; toda mutação exige CSRF. A resposta
de login e o endpoint `me` retornam somente perfil, nome de exibição, vínculo e
unidade aplicáveis. CPF, matrícula, senha e referência interna nunca são
serializados.

As rotas antigas `/api/demo/context/` e `/api/demo/select-profile/` foram
removidas. Chaves `demo_*` remanescentes em sessões antigas são ignoradas e
limpas quando a pessoa autentica.

## Contas de demonstração

O seed cria as contas abaixo apenas com `DEMO_ACCOUNTS_ENABLED=True`, ativado
em local e testes e desativado em produção:

| Perfil | CPF | Senha inicial |
|---|---|---|
| Usuário da Sala | `999.999.999-91` | `Senha123.` |
| Monitor da Sala | `999.999.999-92` | `Senha123.` |
| Supervisor da Biblioteca | `999.999.999-93` | `Senha123.` |

Os CPFs acima têm dígitos verificadores inválidos e só são aceitos como
identificadores de demonstração pelo seed. A reexecução não restaura perfil,
estado ativo ou senha de contas existentes.

## Segurança e evolução

- habilitar HTTPS e cookies seguros em produção;
- manter proteção CSRF e mensagens genéricas de falha de autenticação;
- não registrar senhas nem retornar identificadores de login;
- não inserir credenciais de demonstração em configuração de produção;
- integração institucional, autocadastro, recuperação de senha e conta de
  administrador exigem nova decisão e revisão dos controles antes de permitir
  dados reais.
