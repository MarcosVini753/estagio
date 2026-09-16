# ADR 0026: Reconciliar prazos antes de consultas operacionais

## Status

Aceita.

## Contexto

A reconciliação periódica definida nas ADRs 0019 e 0024 encerra sessões e
cancela reservas vencidas. Entretanto, um processo periódico pode atrasar,
reiniciar ou ficar temporariamente indisponível. Nesse intervalo, uma consulta
poderia apresentar uma sessão como ativa ou um computador como ocupado depois
do prazo, embora o domínio já considerasse esse estado vencido.

Executar a reconciliação dentro das funções puras de disponibilidade esconderia
efeitos persistentes em código de consulta e faria a mesma projeção gravar no
banco quando reutilizada por relatórios, previews ou testes.

## Decisão

As leituras operacionais autorizadas reconciliam os registros relevantes antes
de montar a resposta. A autorização e a validação dos parâmetros acontecem
primeiro; em seguida, a view captura um único `now`, chama o serviço de
reconciliação com escopo explícito e usa o mesmo instante na consulta.

O escopo pode conter computadores, referências de usuário ou período. Quando
computadores e usuários forem informados juntos, a união é observada: um
registro relacionado a qualquer um deles deve ser reconciliado. Períodos
consideram sessões que se sobrepõem ao intervalo, ainda que tenham começado
antes dele.

Uma sessão expira em `now >= exit_deadline_at` e é encerrada no próprio
`exit_deadline_at`. Uma reserva expira somente em
`now > check_in_deadline_at` e registra em `cancelled_at` o instante efetivo do
processamento. Locks pessimistas, ordenação estável e revalidação de estado
tornam rodadas simultâneas idempotentes.

O comando `reconcile_operational_deadlines` continua existindo em execução única
e no modo `--watch`, a cada 60 segundos. Ele cobre períodos sem acesso. A
reconciliação anterior às leituras reduz a defasagem percebida, mas não substitui
o processo periódico.

Esta decisão amplia a reconciliação definida nas ADRs 0019 e 0024. A lógica de
disponibilidade permanece sem efeitos persistentes.

## Consequências

- respostas operacionais não exibem estados vencidos mesmo se a rodada periódica
  atrasar;
- consultas processam apenas o escopo que observam, evitando varrer todo o banco;
- mutações e leituras compartilham as mesmas fronteiras temporais;
- disponibilidade e projeções continuam reutilizáveis como funções de consulta;
- toda implantação duradoura ainda precisa executar o processo periódico;
- leituras operacionais podem realizar pequenas escritas transacionais antes da
  consulta principal.
