# Protótipo navegável

## Localização

O protótipo está em `prototipos/` e utiliza HTML, CSS e JavaScript puro.

## Finalidade

O protótipo serve para:

- validar navegação e hierarquia visual;
- demonstrar os fluxos dos perfis;
- testar o conceito de consulta entre hoje e amanhã;
- simular reserva, sessão, troca de computador, ocorrências e relatórios;
- apoiar conversas com a supervisão da biblioteca.

## O que não deve ser inferido do protótipo

- o formato dos objetos em `localStorage` não define o banco;
- `statusToday` e `statusTomorrow` não devem existir no modelo definitivo;
- `busy` e `reserved` não são estados operacionais persistidos;
- a escolha de perfil não é autenticação;
- os números e usuários simulados não representam dados reais;
- regras implementadas somente no frontend devem ser reimplementadas e testadas no domínio do backend.

## Perfis simulados

A tela inicial deve permitir selecionar:

- Usuário da Sala;
- Estagiário;
- Supervisor da Biblioteca;
- Administrador do Sistema, quando houver telas de demonstração administrativa.

O perfil selecionado controla navegação e ações disponíveis durante o teste.

## Ajustes obrigatórios antes da integração com o backend

- remover qualquer referência a fila de espera;
- usar Estagiário em lugar de Servidor da Biblioteca;
- separar estado operacional de estado efetivo;
- permitir reserva apenas para amanhã;
- permitir uso imediato somente hoje;
- impedir horários já passados;
- substituir dados de uso agregados simulados por sessões e alocações reais;
- substituir `localStorage` gradualmente pela API `/api/v1/`.

## Estratégia de migração

1. preservar o protótipo atual como referência;
2. criar templates e componentes visuais equivalentes;
3. implementar endpoints de disponibilidade;
4. integrar reservas;
5. integrar sessões e alocações;
6. integrar ocorrências;
7. integrar relatórios;
8. remover estado local que duplique dados do servidor.

## Critério de fidelidade

A implementação não precisa reproduzir cada detalhe do código do protótipo, mas deve preservar os fluxos validados, a simplicidade da navegação e a experiência responsiva.
