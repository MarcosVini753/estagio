# ADR 0013: Manter Administrador como papel arquitetural

## Status

Aceita

## Contexto

Os casos de uso detalhados atuais concentram-se em Usuário da Sala, Monitor da Sala e Supervisor, mas o sistema prevê administração de contas, permissões, parâmetros e logs.

## Decisão

Manter `SYSTEM_ADMIN` como papel arquitetural. Nesta etapa, ele não possui conta nem login; provisionamento de conta administrativa e seus casos de uso detalhados permanecem fora do escopo.

## Alternativas consideradas

- eliminar o papel até a implementação da autenticação;
- atribuir todas as funções administrativas ao Supervisor;
- usar somente superusuário técnico sem papel funcional.

## Consequências positivas

- evita confundir gestão da biblioteca com administração do sistema;
- prepara a futura adoção de contas e permissões;
- mantém limites claros de responsabilidade.

## Consequências negativas e riscos

- o código de papel permanece nos modelos de auditoria e regras arquiteturais, sem estar disponível como conta operacional;
- a documentação deve distinguir capacidade arquitetural de funcionalidade entregue;
- uma conta administrativa exige decisão e controles próprios; o login operacional não a cria implicitamente.
