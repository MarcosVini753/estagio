# ADR 0014: Identidade fictícia e snapshots analíticos

## Status

Aceita; identidade de acesso atualizada pela ADR 0027

## Contexto

O perfil de demonstração sozinho não diferencia usuários da sala nem permite agrupamento histórico por vínculo e unidade. A decisão original evitava persistir contas; a ADR 0027 posteriormente aprovou contas operacionais locais sem integração institucional.

## Decisão

Persistir referência operacional opaca, tipo de vínculo e unidade institucional na conta de Usuário da Sala e copiar os snapshots para `Reservation` e `UseSession` no momento da criação. Registros anteriores continuam usando `NOT_INFORMED` e unidade vazia, sem atribuição automática a novas contas.

## Consequências

- relatórios históricos não dependem do contexto atual;
- a referência operacional não é CPF/matrícula e não expõe o identificador de login;
- login local usa senha com hash e sessão, sem token ou integração institucional;
- a titularidade histórica não é reconstruída automaticamente.
