# Módulos do backend

O backend será dividido em apps Django por domínio. A separação não implica microsserviços.

## `core`

Responsabilidades compartilhadas:

- classes base com timestamps;
- utilitários de data e horário;
- respostas de erro padronizadas;
- constantes e tipos comuns;
- health check.

Não deve concentrar regras específicas de reservas, sessões ou relatórios.

## `access`

Responsável, no MVP, por:

- perfis de teste;
- armazenamento temporário do perfil selecionado;
- políticas de autorização simulada;
- endpoint para consultar e alterar o contexto de demonstração.

A autenticação real será tratada em etapa futura. O nome `access` evita criar prematuramente um modelo de usuário definitivo.

## `configuration`

Responsável por:

- turnos;
- calendários semanais regulares e temporários;
- resolução do horário de funcionamento;
- exceções de calendário;
- avisos internos;
- parâmetros de reserva;
- parâmetros de relatório.

Entidades:

- `Shift`;
- `OperatingSchedule`;
- `OperatingScheduleDay`;
- `OperatingWindow`;
- `CalendarException`;
- `RoomNotice`;
- `BookingPolicy`;
- `ReportConfiguration`.

## `computers`

Responsável por:

- cadastro de computadores;
- estado operacional;
- histórico de mudanças de estado;
- consultas básicas de inventário.

Entidades:

- `Computer`;
- `ComputerOperationalStateChange`.

## `operations`

Núcleo transacional do sistema:

- disponibilidade;
- reservas;
- entrada;
- sessão ativa;
- alocações;
- troca de computador;
- saída;
- correções operacionais;
- orquestração atômica da indisponibilidade de computadores;
- realocação e cancelamento operacional de reservas.

Entidades:

- `Reservation`;
- `UseSession`;
- `ComputerAllocation`;
- `SessionCorrection` ou eventos de correção auditáveis.

## `occurrences`

Responsável por:

- registro de problemas;
- consulta e tratamento de ocorrências;
- associação com computador, sessão e alocação.

Entidade:

- `Occurrence`.

## `reports`

Responsável por consultas analíticas e exportações:

- relatório diário;
- mensal;
- anual;
- ocupação;
- uso por computador;
- uso por curso, setor e vínculo;
- reservas e cancelamentos.

Deve possuir principalmente selectors, projections e exporters. Não deve criar lançamentos manuais de totais.
O relatório semanal permanece como evolução futura, fora da Etapa 4.

## `audit`

Responsável por eventos administrativos sensíveis:

- alteração de estado operacional;
- correção de registros;
- mudança de parâmetros;
- criação, substituição ou edição de calendário e exceção;
- publicação ou desativação de aviso;
- realocação ou cancelamento de reserva por mudança operacional;
- ações futuras de contas e permissões.

Entidade futura ou inicial:

- `AuditEvent`.

## Dependências permitidas

```text
access ───────────────┐
configuration ────────┼──> operations
computers ────────────┘
operations ──────────────> occurrences
operations ──────────────> reports
configuration ───────────> reports
computers ───────────────> reports
occurrences ─────────────> reports
```

## Regras de dependência

- `computers` não depende de `operations` para persistência; estados efetivos são consultados por serviço de disponibilidade.
- `reports` pode ler os demais domínios, mas os demais domínios não dependem de `reports`.
- `audit` recebe eventos ou chamadas dos serviços, sem conter lógica de negócio principal.
- evitar imports circulares; usar IDs, serviços e interfaces quando necessário.
