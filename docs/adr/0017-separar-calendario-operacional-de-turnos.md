# ADR 0017: Separar calendário operacional de turnos

## Status

Aceita.

## Contexto

`Shift` acumulava duas responsabilidades: classificar sessões e delimitar as janelas em que a sala estava aberta. A disponibilidade transformava todos os turnos válidos de uma data em funcionamento. Como o modelo não representa dia da semana, sábado à tarde e domingo eram tratados como abertos sempre que havia turnos vigentes.

Alterar um turno para corrigir relatórios também alterava reservas e entrada imediata. Adicionar somente um campo `weekday` manteria essa dependência entre conceitos com ciclos de vida diferentes e dificultaria recessos, exceções e preservação histórica.

## Alternativas consideradas

- adicionar `weekday` a `Shift` e continuar derivando abertura dos turnos;
- codificar sábado e domingo diretamente no gerador de slots;
- manter um único calendário editável e restaurá-lo manualmente depois de cada recesso;
- criar calendário operacional versionado, independente dos turnos analíticos.

## Decisão

Criar `OperatingSchedule`, `OperatingScheduleDay` e `OperatingWindow` no domínio `configuration`. Um calendário é `REGULAR` ou `TEMPORARY`, configura exatamente os sete dias e aceita múltiplas janelas sem sobreposição em um dia aberto.

Calendários ativos do mesmo tipo não se sobrepõem. Horário temporário exige data final. Versões de um mesmo calendário compartilham `series_key`; uma substituição futura encerra a versão anterior no dia precedente e preserva o histórico.

A resolução para uma data segue:

```text
1. CalendarException da data
2. OperatingSchedule TEMPORARY aplicável
3. OperatingSchedule REGULAR aplicável
4. OPERATING_SCHEDULE_REQUIRED
```

O calendário regular inicial é de segunda a sexta, 07h15–21h; sábado, 07h15–13h; domingo explicitamente fechado. Ao terminar um horário temporário, o regular volta a ser efetivo sem nova escrita.

`Shift` continua versionado e é usado apenas para classificar a sessão pelo horário de entrada e agrupar relatórios.

Mudanças que tornem reservas confirmadas incompatíveis exigem preview e confirmação. A confirmação invalida as reservas na mesma transação, registra metadados e auditoria e faz com que deixem de bloquear disponibilidade.

Avisos operacionais usam `RoomNotice`, uma comunicação interna geral com período efetivo e período de visibilidade. A criação vinculada a calendário ou exceção ocorre na mesma transação. E-mail, SMS, push e destinatários individuais permanecem fora do MVP.

## Consequências positivas

- sábado e domingo são representados explicitamente;
- recessos deixam de exigir restauração manual;
- exceções pontuais têm precedência determinística;
- alterações analíticas de turno não mudam a abertura;
- disponibilidade, sessões e relatórios usam a mesma resolução;
- reservas afetadas e comunicações preservam histórico auditável.

## Consequências negativas e riscos

- o domínio ganha três entidades de calendário e uma de aviso;
- alterações administrativas exigem transação e bloqueio de reservas;
- uma configuração incompleta impede cálculo silencioso e retorna erro explícito;
- a primeira implementação de avisos é apenas informativa e usa perfis simulados.
