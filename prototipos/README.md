# Protótipo navegável

O protótipo em HTML, CSS e JavaScript puro representa a experiência visual discutida antes da implementação Django.

## Execução

Abra `index.html` no navegador.

## Limitações

Os dados são fictícios e persistidos em `localStorage`. Não há backend, autenticação ou segurança. O protótipo não define o banco de dados.

## Regras para ajustes futuros

- perfis: Usuário da Sala, Estagiário, Supervisor e Administrador;
- seleção de perfil apenas simulada;
- consulta para hoje e amanhã;
- uso imediato somente hoje;
- reserva para horário futuro de hoje ou para amanhã;
- horários passados indisponíveis;
- sem fila de espera;
- estado operacional persistido: `AVAILABLE`, `MAINTENANCE`, `INACTIVE`;
- `OCCUPIED` e `RESERVED` calculados;
- troca preserva uma sessão com várias alocações;
- relatórios derivados de registros operacionais.

A integração real deve usar a API `/api/v1/` e evitar duas fontes de verdade.
