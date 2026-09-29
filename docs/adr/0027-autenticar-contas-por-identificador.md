# ADR 0027: Autenticar contas operacionais por CPF ou matrícula

## Status

Aceita

## Contexto

A seleção pública de perfil permitia assumir qualquer papel e misturava
identidade operacional com dados guardados na sessão. Reservas, sessões e
ocorrências precisam pertencer a uma conta estável para que as consultas
individuais não confundam pessoas. Ao mesmo tempo, o MVP ainda não dispõe de
integração de identidade institucional nem pode usar credenciais de demonstração
com dados reais.

## Decisão

- autenticar contas operacionais com usuário/senha do Django e sessão;
- permitir login por CPF pontuado ou sem pontuação, ou por matrícula;
- vincular cada usuário Django a `AccessAccount`, que guarda perfil, nome de
  exibição, referência operacional opaca e dados institucionais necessários;
- guardar os identificadores separados em `LoginIdentifier`, únicos no sistema
  após normalização; uma conta pode ter CPF, matrícula ou ambos;
- armazenar senhas usando o hasher nativo do Django, exigir CSRF em login,
  logout e demais mutações, e encerrar a sessão explicitamente por logout;
- usar cookie de sessão que expira ao fechar o navegador;
- não oferecer autocadastro, recuperação de senha ou escolha de perfil;
- não provisionar conta `SYSTEM_ADMIN`; este papel continua apenas arquitetural;
- manter credenciais especiais e compartilhadas somente em local/teste, sem
  criá-las ou redefini-las em produção;
- não atribuir automaticamente registros operacionais históricos às contas
  novas.

O comando `create_access_account` provisiona contas futuras de forma interna e
solicita senha interativamente. Os CPFs fictícios fornecidos para a demonstração
possuem dígitos verificadores inválidos e só são aceitos pelo seed local/teste.

## Alternativas consideradas

- manter a seleção pública de perfil: não estabelece identidade nem propriedade
  de registros;
- integrar SSO institucional: fora do alcance operacional e de infraestrutura
  deste MVP;
- criar autenticação JWT: desnecessária para páginas e API servidas pelo mesmo
  monólito com sessão e CSRF;
- usar CPF como referência operacional: exporia dado pessoal nos registros e
  acoplaria o histórico ao identificador de login.

## Consequências positivas

- operações “minhas” ficam isoladas por referência estável da conta;
- o perfil não pode ser escolhido por payload ou sessão antiga;
- senha nunca é armazenada em texto puro;
- HTML e API compartilham a mesma conta, sessão e fonte de autorização;
- uma conta pode usar CPF e matrícula sem duplicar sua identidade operacional.

## Consequências e riscos

- credenciais de demonstração são compartilhadas e fracas para uso real; devem
  ficar restritas a ambiente controlado com dados fictícios;
- provisionamento e revogação ainda são operações internas;
- dados históricos preservam seus totais, mas não aparecem como pertencentes a
  uma conta nova;
- integração institucional, recuperação de senha, políticas de ciclo de vida e
  conta administrativa precisam de decisões próprias antes de uso real.
