# ADR 0013: Manter Administrador como papel arquitetural

## Status

Aceita

## Contexto

Os casos de uso detalhados atuais concentram-se em Usuário da Sala, Estagiário e Supervisor, mas o sistema prevê administração de contas, permissões, parâmetros e logs.

## Decisão

Manter `SYSTEM_ADMIN` como papel arquitetural, mesmo que sua autenticação real e seus casos de uso detalhados sejam implementados em etapa futura.

## Alternativas consideradas

- eliminar o papel até a implementação da autenticação;
- atribuir todas as funções administrativas ao Supervisor;
- usar somente superusuário técnico sem papel funcional.

## Consequências positivas

- evita confundir gestão da biblioteca com administração do sistema;
- prepara a futura adoção de contas e permissões;
- mantém limites claros de responsabilidade.

## Consequências negativas e riscos

- o seletor de perfil pode exibir um papel ainda sem telas completas;
- a documentação deve distinguir capacidade arquitetural de funcionalidade entregue;
- não se deve implementar autenticação real implicitamente sem novo ADR.
