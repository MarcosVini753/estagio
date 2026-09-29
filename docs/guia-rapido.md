# Guia rápido

## O que é este sistema

Um sistema web para controlar o uso da Sala de Informática da Biblioteca da UFAC. Ele substitui o registro manual de entrada e saída, permite reservar computadores, acompanhar a operação em tempo real e gerar relatórios a partir dos registros reais.

## Como funciona na prática

1. A pessoa entra com CPF ou matrícula e senha; o perfil e as permissões vêm da conta, não de uma escolha na tela.
2. Consulta a disponibilidade de **hoje** ou **amanhã**.
3. **Hoje**: pode iniciar uso imediato em um computador livre, escolhendo a saída planejada em uma grade de 15 minutos.
4. **Amanhã (ou horário futuro de hoje)**: pode reservar um ou mais slots consecutivos.
5. Em uma reserva, a entrada pode ser registrada de 3 minutos antes até 3 minutos depois do início. O sistema registra a sessão com um **fim planejado**; as tolerâncias operacionais não aparecem na área do usuário.
6. Durante a sessão, o usuário pode **trocar de computador** sem perder o histórico.
7. Ao sair, a sessão é encerrada. Se o usuário não sair até o prazo, o sistema encerra logicamente.
8. O Monitor acompanha a sala, corrige registros e trata ocorrências. O Supervisor configura horários e gera relatórios.

## As 8 regras essenciais

1. Consulta de disponibilidade somente para **hoje e amanhã**.
2. Uso imediato somente **hoje**; reservas para hoje (futuro) ou amanhã.
3. **Sem fila de espera**.
4. Computador persiste apenas `AVAILABLE`, `MAINTENANCE` ou `INACTIVE`. `OCCUPIED` e `RESERVED` são calculados.
5. Um usuário tem no máximo **uma sessão ativa**; um computador, **uma alocação ativa**.
6. Trocar de computador **não cria nova sessão** nem apaga histórico.
7. Relatórios são **projeções** dos registros operacionais — não há lançamento manual.
8. O login usa sessão Django e senha armazenada com hash; integração institucional, autocadastro e conta de Administrador não fazem parte do MVP.

No ambiente local, `make seed` cria três contas de demonstração: CPF
`999.999.999-91` para Usuário da Sala, `999.999.999-92` para Monitor e
`999.999.999-93` para Supervisor. Todas usam `Senha123.`. São credenciais
compartilhadas e fictícias, exclusivas para ambiente local/controlado; nunca as
use com dados reais. O seed não redefine contas alteradas e não cria essas
contas em produção.

## Onde está cada coisa

| Você quer... | Leia |
|---|---|
| Entender o produto e as regras | `docs/product/00-visao-geral.md` e `docs/product/03-regras-de-negocio.md` |
| Entender a arquitetura e os módulos | `docs/architecture/00-visao-geral.md` |
| Ver o modelo de dados | `docs/architecture/02-modelo-de-dominio.md` e `docs/architecture/diagrams/erd.md` |
| Usar a API | `docs/architecture/04-api.md` (ou `/api/docs/` no navegador) |
| Ver o estado da implementação | `docs/architecture/08-estado-implementacao.md` |
| Entender decisões arquiteturais | `docs/adr/README.md` |
| Ver diagramas de fluxo | `docs/diagrams/README.md` |
| Rodar o backend | `docs/development/backend-setup.md` |
| Usar a interface do Usuário da Sala | Entre com o CPF de Usuário da Sala acima |
| Usar o painel operacional | Entre com o CPF de Monitor acima |
| Usar configurações e relatórios | Entre com o CPF de Supervisor acima |
| Ver o protótipo visual | `prototipos/` |

## Como rodar o backend em 5 comandos

```bash
cp .env.example .env
python -m venv .venv && source .venv/bin/activate
make install
docker compose up -d db
make migrate && make seed && make run
```

A aplicação fica em `http://localhost:8000/` e a documentação da API em `http://localhost:8000/api/docs/`.

Para preencher Diário, Mensal, Anual e Indicadores com uma linha do tempo
fictícia, execute `make seed-reports` somente em banco descartável. Na área do
Supervisor, os três botões de download geram CSV, planilha XLSX e PDF a partir
dos mesmos números exibidos na tela.

Se a porta `5432` já estiver ocupada, ajuste `POSTGRES_PORT` no `.env` para uma
porta livre, como `5433`. O Compose e os comandos `make` usarão o mesmo valor.
