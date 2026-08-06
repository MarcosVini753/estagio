# Protótipo navegável

O diretório `prototipos/` contém a referência visual original em HTML, CSS e JavaScript puro.

## Finalidade

- validar navegação e hierarquia visual;
- demonstrar os fluxos dos perfis;
- apoiar validação com a biblioteca;
- orientar a migração para Django Templates.

## Não inferir do protótipo

- objetos de `localStorage` não definem o banco;
- `statusToday`, `statusTomorrow`, `busy` e `reserved` não são campos persistidos;
- escolha de perfil não é autenticação;
- dados simulados não representam pessoas reais;
- regras somente no frontend devem ser reimplementadas no backend.

## Ajustes durante a integração

- não introduzir fila de espera;
- usar Monitor da Sala, não Servidor da Biblioteca;
- separar estado operacional de estado efetivo;
- permitir reserva de slots consecutivos para horário futuro de hoje ou para amanhã;
- permitir uso imediato somente hoje, com duração escolhida antes da entrada;
- exibir fim planejado e prazo de saída três minutos depois;
- impedir intervalo que atravesse reserva ou fechamento;
- impedir horários passados;
- substituir agregados simulados por sessões e alocações;
- substituir gradualmente `localStorage` pela API `/api/`.

## Estado atual

A tela mínima de seleção de perfil já existe em Django. O protótipo completo ainda não foi migrado e continua sendo apenas referência visual.
