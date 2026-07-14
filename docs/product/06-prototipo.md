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
- usar Estagiário, não Servidor da Biblioteca;
- separar estado operacional de estado efetivo;
- permitir reserva para horário futuro de hoje ou para amanhã;
- permitir uso imediato somente hoje;
- impedir horários passados;
- substituir agregados simulados por sessões e alocações;
- substituir gradualmente `localStorage` pela API `/api/v1/`.

## Estado atual

A tela mínima de seleção de perfil já existe em Django. O protótipo completo ainda não foi migrado e continua sendo apenas referência visual.
