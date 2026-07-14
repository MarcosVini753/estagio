# Protótipo navegável

O protótipo em HTML, CSS e JavaScript puro representa a experiência visual e os fluxos já discutidos para o sistema.

## Execução

Abra `index.html` no navegador.

## Estado atual

Os dados são simulados e persistidos em `localStorage`. O protótipo não possui backend, autenticação real ou segurança.

## Regras que devem orientar ajustes futuros

- perfis: Usuário da Sala, Estagiário, Supervisor e Administrador;
- a seleção de perfil é apenas uma simulação;
- consulta somente para hoje e amanhã;
- uso imediato somente hoje;
- reserva somente amanhã;
- horários passados não podem ser usados;
- não existe fila de espera;
- computadores persistem somente estados operacionais `AVAILABLE`, `MAINTENANCE` e `INACTIVE` no backend futuro;
- ocupado e reservado são situações calculadas;
- troca de computador preserva uma única sessão com várias alocações;
- relatórios serão calculados a partir de registros reais.

## Relação com a implementação

Este diretório é referência visual. O modelo de dados e as regras oficiais estão em `docs/product/` e `docs/architecture/`.

Durante a migração, funcionalidades devem ser substituídas gradualmente por chamadas à API `/api/v1/`, evitando manter duas fontes de verdade no navegador e no servidor.
