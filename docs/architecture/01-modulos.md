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
- horário de funcionamento;
- exceções de calendário;
- parâmetros de reserva;
- parâmetros de relatório.

Entidades iniciais:

- `Shift`;
- `CalendarException`;
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
- correções operacionais.

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
- semanal;
- mensal;
- anual;
- ocupação;
- uso por computador;
- uso por curso, setor e vínculo;
- reservas, cancelamentos e não comparecimentos.

Deve possuir principalmente selectors, projections e exporters. Não deve criar lançamentos manuais de totais.

## `audit`

Responsável por eventos administrativos sensíveis:

- alteração de estado operacional;
- correção de registros;
- mudança de parâmetros;
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
