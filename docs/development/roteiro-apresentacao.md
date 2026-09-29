# Roteiro didático para a apresentação do sistema

Este guia ajuda a preparar uma apresentação de **15 minutos** do Sistema de
Controle de Uso da Sala de Informática da Biblioteca da UFAC. Ele não substitui
o trabalho acadêmico nem os slides: organiza a fala, a demonstração e os vídeos
para que cada elemento explique uma parte do produto.

## Resultado que a banca deve compreender

Ao terminar, a banca deve conseguir responder três perguntas:

1. **Qual problema foi resolvido?** O controle manual de uso dificulta o
   acompanhamento da sala e a consolidação confiável de informações.
2. **Como o sistema resolve esse problema?** Ele registra reservas, sessões,
   alocações, estados operacionais e ocorrências aplicando regras transacionais.
3. **Que resultado isso gera?** A operação fica acompanhável por Monitor e
   Supervisor, e os relatórios são calculados a partir de registros reais, não
   preenchidos manualmente.

A frase que guia toda a apresentação pode ser:

> O sistema transforma o controle manual da sala em registros operacionais
> confiáveis, acompanhamento por perfil e relatórios consolidados.

## Limites honestos do MVP

Explique estes limites com naturalidade se surgirem perguntas:

- o login local usa CPF ou matrícula e senha; não há integração institucional
  nem uso autorizado de dados reais;
- a consulta de disponibilidade é limitada a hoje e amanhã;
- não existe fila de espera;
- relatórios são projeções de reservas, sessões, alocações, ocorrências,
  calendário e estados operacionais já registrados;
- a interface e conta do Administrador e autenticação institucional são
  evoluções futuras.

Essas limitações não diminuem a entrega. Elas demonstram que o escopo foi
definido conscientemente. Consulte a [visão geral do produto](../product/00-visao-geral.md)
para explicar o problema e as restrições sem improvisar.

## Estrutura e tempo total

Use um cronômetro nos ensaios. O tempo entre colchetes é um teto, não uma meta
para preencher com mais texto.

| Bloco | Tempo | Objetivo |
| --- | ---: | --- |
| Contexto e projeto | 5 min | Explicar por que o sistema existe e como foi pensado. |
| Produto e demonstração | 10 min | Provar o valor por meio das telas e dos fluxos reais. |

Reserve os últimos 30 a 45 segundos para encerrar. Essa margem absorve a troca
de perfil, o carregamento de uma tela ou uma pequena pergunta sem comprometer o
fim da apresentação.

## Parte 1 — contexto e projeto (até 5 minutos)

### Slide 1 — capa [0:00–0:20]

**Coloque:**

- título do trabalho;
- nome do aluno ou da equipe;
- nome do orientador;
- curso, instituição e data, se exigidos pela disciplina.

**Fala sugerida:**

> Bom dia. Meu nome é [nome] e apresentarei o Sistema de Controle de Uso da
> Sala de Informática da Biblioteca da UFAC, desenvolvido sob orientação de
> [nome].

Não explique tecnologias ou requisitos neste momento. A capa serve apenas para
identificar o trabalho e iniciar com segurança.

### Slide 2 — agenda [0:20–0:35]

**Coloque:** `Problema → proposta → arquitetura → demonstração → resultado`.

**Fala sugerida:**

> Primeiro contextualizo o problema e as decisões principais. Em seguida,
> mostrarei o sistema funcionando para os perfis que participam da operação.

A agenda deve ser uma linha simples. Ela orienta a banca e evita que a
apresentação pareça uma sequência de telas desconexas.

### Slide 3 — problema e objetivo [0:35–1:20]

**Visual recomendado:** duas colunas, com “controle manual” à esquerda e
“controle operacional rastreável” à direita. Use ícones ou pouco texto.

**Explique em linguagem simples:**

- registrar entrada e saída manualmente produz retrabalho e erros;
- é difícil descobrir quem usou qual computador e em que período;
- consolidar relatórios posteriormente consome tempo e pode não refletir o uso
  real;
- a proposta é registrar a operação no momento em que ela acontece.

**Fala sugerida:**

> O problema não é apenas anotar uma entrada. Sem registros estruturados,
> reservas, trocas de computador, indisponibilidades e ocorrências ficam
> dispersas. O objetivo foi criar uma aplicação web que registre esses fatos e
> gere análises diretamente a partir deles.

### Slide 4 — atores e proposta [1:20–1:55]

**Visual recomendado:** três cartões com os perfis principais.

| Perfil | O que a apresentação deve associar a ele |
| --- | --- |
| Usuário da Sala | consulta disponibilidade, reserva, usa computador e informa problema; |
| Monitor da Sala | acompanha a operação, trata ocorrências e corrige registros autorizados; |
| Supervisor da Biblioteca | configura a operação e analisa relatórios e indicadores. |

**Fala sugerida:**

> A mesma informação operacional atende necessidades diferentes. O usuário
> precisa de uma experiência direta de uso; o monitor precisa acompanhar a
> sala; e o supervisor precisa transformar os registros em decisão gerencial.

Não apresente o Administrador como uma tela pronta. Diga, se necessário, que
ele existe como papel arquitetural, mas sua interface própria não faz parte do
MVP atual.

### Slide 5 — tecnologias e decisões [1:55–2:35]

**Coloque apenas o necessário:**

- Django 5.2 e Django REST Framework;
- PostgreSQL;
- Django Templates, HTMX, Alpine.js e Tailwind CSS;
- Docker Compose;
- testes Django, Playwright, OpenAPI e CI.

**Fala sugerida:**

> A solução é um monólito modular em Django. As regras críticas ficam em
> serviços transacionais; PostgreSQL protege invariantes persistentes; e o
> frontend usa renderização no servidor com melhoria progressiva, sem exigir
> uma SPA para o fluxo funcionar.

Evite explicar cada biblioteca. O ponto é relacionar a tecnologia ao efeito:
integridade, simplicidade de manutenção, interface responsiva e validação.

### Slide 6 — requisitos [2:35–3:20]

**Visual recomendado:** duas colunas de no máximo quatro itens cada.

| Funcionais | Não funcionais |
| --- | --- |
| consultar disponibilidade e reservar; | integridade e concorrência no banco; |
| iniciar, trocar e encerrar uso; | auditoria de ações sensíveis; |
| registrar ocorrências e estados operacionais; | interface responsiva e acessível; |
| consolidar e exportar relatórios. | testes automatizados e contrato OpenAPI. |

**Fala sugerida:**

> Os requisitos funcionais descrevem o que cada perfil consegue fazer. Os não
> funcionais protegem a qualidade do resultado: por exemplo, não basta mostrar
> um computador disponível se uma sessão concorrente pode ocupá-lo no mesmo
> instante.

Essa explicação liga requisitos técnicos à experiência real da pessoa que usa a
sala.

### Slide 7 — diagramas e protótipos [3:20–4:30]

Mostre **no máximo dois diagramas**. Muitos diagramas pequenos fazem a banca
parar de acompanhar a ideia central.

1. Use o [diagrama C4 de contêiner](../architecture/diagrams/c4-container.md)
   para apresentar navegador, aplicação Django e PostgreSQL.
2. Use o [fluxo de consulta e agendamento](../diagrams/atividades/01-usuario-consultar-e-agendar.puml)
   ou o [fluxo de relatório consolidado](../diagrams/atividades/11-supervisor-gerar-relatorio-consolidado.puml)
   para mostrar uma regra importante do produto.

Ao lado, inclua uma captura de tela real da aplicação ou uma referência curta
ao [protótipo](../../prototipos/). O protótipo explica a intenção visual; a
aplicação é a evidência de que o comportamento foi implementado.

**Fala sugerida:**

> A arquitetura separa a interface, as regras do domínio e a persistência. O
> diagrama de fluxo mostra que uma reserva não é só um formulário: a aplicação
> consulta o calendário, valida conflitos e só então registra a operação.

### Transição para a demonstração [4:30–5:00]

**Fala sugerida:**

> A partir daqui, vou mostrar como essas regras aparecem para quem utiliza,
> acompanha e administra a sala.

Enquanto faz a transição, abra a aplicação já preparada. Não execute comandos,
instale dependências ou procure arquivos diante da banca.

## Parte 2 — produto desenvolvido (até 10 minutos)

### Visão geral da demonstração

A ordem deve ser sempre a mesma:

```text
Usuário da Sala → Monitor da Sala → Supervisor da Biblioteca → resultado
```

Ela reproduz o caminho da informação: uma ação de uso gera um registro, o
Monitor acompanha a operação e o Supervisor consulta o resultado consolidado.

| Momento | Tempo | Demonstração | Mensagem |
| --- | ---: | --- | --- |
| Abertura e acesso | 5:00–5:30 | login de demonstração e aviso de ambiente fictício | a conta define o perfil; credenciais compartilhadas servem apenas para demonstração; |
| Usuário | 5:30–7:20 | disponibilidade, reserva ou uso, agenda/sessão | a pessoa consegue se orientar sem conhecer as regras internas; |
| Monitor | 7:20–8:45 | painel, estado operacional ou ocorrência | a operação é acompanhada sem alterar dados arbitrariamente; |
| Supervisor | 8:45–10:45 | relatórios e exportação | os indicadores derivam dos registros reais; |
| Vídeos | 10:45–12:30 | dois fluxos curtos | cobrem cenários temporais ou longos; |
| Resultado e encerramento | 12:30–14:30 | síntese e próximos passos | retoma problema, solução e limites; |
| Margem | 14:30–15:00 | pausa ou pergunta | preserva o término no prazo. |

### Demonstração 1 — Usuário da Sala [5:30–7:20]

**Objetivo:** provar que a pessoa vê disponibilidade real e que o servidor
aplica as regras, sem transferir cálculos críticos para o navegador.

**Sequência sugerida:**

1. Escolha **Usuário da Sala** e preencha a identificação fictícia solicitada.
2. Abra **Computadores** e explique a diferença entre o funcionamento da sala
   e o estado efetivo de cada computador.
3. Alterne entre hoje e amanhã ou use a busca para mostrar que a disponibilidade
   é consultada no servidor.
4. Abra um computador e mostre uma reserva futura ou o início de uso imediato.
5. Mostre **Agenda** ou **Sessão** para concluir que a ação gerou um registro.

**Fala sugerida:**

> O usuário vê somente o que precisa decidir: se a sala está funcionando, quais
> computadores podem ser utilizados e quais horários estão disponíveis. As
> regras de conflitos, calendário e prazo ficam no servidor, evitando que uma
> decisão visual gere uma reserva inválida.

**Ponto importante:** não exponha a tolerância operacional de três minutos
como se fosse uma instrução para o usuário. Ela é uma regra interna. A tela
mostra entrada real e saída planejada.

### Demonstração 2 — Monitor da Sala [7:20–8:45]

**Objetivo:** mostrar que o Monitor atua sobre a operação, mas não altera os
estados calculados diretamente.

**Sequência sugerida:**

1. Saia da conta anterior e entre com o CPF de demonstração do **Monitor da Sala**.
2. Abra o painel ou a listagem de computadores e sessões ativas.
3. Mostre uma ocorrência ou altere o estado persistido de um computador para
   manutenção, se a massa de demonstração permitir.
4. Explique o efeito apresentado pela própria tela: sessões, realocações,
   encerramentos ou reservas afetadas são tratados com regras e auditoria.

**Fala sugerida:**

> Disponível, manutenção e inativo são estados operacionais persistidos. Já
> ocupado e reservado são estados calculados a partir das sessões e reservas.
> Essa separação evita que alguém marque manualmente um computador como livre
> quando ainda existe uma alocação ativa.

### Demonstração 3 — Supervisor da Biblioteca [8:45–10:45]

**Objetivo:** conectar registros operacionais à análise gerencial.

**Sequência sugerida:**

1. Troque para **Supervisor da Biblioteca**.
2. Abra **Relatórios**.
3. Mostre a visão mensal e alterne rapidamente para Diário, Anual e
   Indicadores.
4. Aponte calendário efetivo, turnos, totais e avisos de dados históricos, se
   houver.
5. Baixe um CSV, XLSX ou PDF já configurado como preferência.

**Fala sugerida:**

> Não existe lançamento manual de total. O relatório usa reservas, sessões,
> alocações, ocorrências, calendário e estados operacionais. Por isso, uma
> correção legítima no registro operacional é refletida imediatamente na
> projeção.

Ao explicar taxa de ocupação, use uma formulação precisa:

> Ela compara o tempo de alocações reais com o tempo em que o computador esteve
> disponível dentro do calendário. O sistema mede uso observado, não tentativas
> recusadas ou demanda reprimida.

## Vídeos de apoio [10:45–12:30]

Prepare dois vídeos silenciosos, cada um com 45 a 60 segundos. Narre ao vivo;
isso permite adaptar o ritmo e responder à reação da banca.

### Vídeo 1 — ciclo de uso

Mostre uma reserva, entrada associada, troca de computador e saída. Narre:

> A troca encerra somente a alocação atual; a sessão permanece a mesma e o
> histórico continua explicando todos os computadores utilizados.

### Vídeo 2 — cenário que depende de tempo ou configuração

Escolha apenas um:

- alteração operacional que impacta reserva ou sessão;
- horário especial ou fechamento excepcional do calendário;
- atualização de relatório após registros históricos de demonstração.

Narre o que tornou o cenário relevante. Não use o vídeo para mostrar cliques
sem contexto.

## Preparação do ambiente

Faça a preparação em um banco local de demonstração, nunca em dados reais. Com
o ambiente Python já configurado, execute antes do ensaio ou da apresentação:

```bash
make db-up
make migrate
make seed
make seed-reports
make run
```

`make seed-reports` executa a semente histórica de relatórios com redefinição
dos dados de demonstração de relatórios. Use-o apenas no ambiente descartável
da apresentação.

Abra `http://localhost:8000/` e mantenha uma segunda aba já posicionada na
tela de Relatórios. Desative notificações, atualizações automáticas do sistema
operacional e qualquer extensão do navegador que possa interferir na gravação.

### Plano A e plano B

| Situação | Plano A | Plano B |
| --- | --- | --- |
| Horário atual fora do funcionamento da sala | demonstrar amanhã e relatórios | usar vídeo do ciclo de uso; |
| Reserva ou sessão não está no estado esperado | mostrar consulta e Agenda | reproduzir a conclusão no vídeo; |
| Navegador ou rede local falha | abrir dados já carregados | usar vídeos e capturas de tela; |
| Tempo está curto | manter problema, requisitos e uma demo completa | omitir detalhes técnicos e o segundo vídeo. |

Não tente corrigir uma falha complexa durante a apresentação. Diga brevemente
que o fluxo está gravado em ambiente controlado e siga o roteiro.

## Como gravar os vídeos

Use OBS Studio, ShareX, o gravador do Windows ou ferramenta equivalente.

- grave em 1920×1080 ou na resolução do projetor;
- use o navegador em zoom que deixe textos legíveis à distância;
- mova o cursor devagar e pause por um segundo ao mudar de tela;
- grave em MP4/H.264, de preferência sem áudio, para narrar ao vivo;
- reproduza o arquivo no computador e no projetor que serão usados;
- mantenha o arquivo e uma cópia local, sem depender de internet.

Antes de gravar, aplique a semente e siga exatamente o roteiro. Assim, o vídeo
e a demonstração usam os mesmos termos e dados fictícios.

## O que evitar

- ler textos longos nos slides;
- mostrar todas as telas, endpoints ou migrations;
- diminuir diagramas até ficarem ilegíveis;
- dizer que existe integração institucional/SSO, fila de espera ou demanda reprimida;
- chamar `OCCUPIED` e `RESERVED` de estados persistidos;
- afirmar que relatórios são preenchidos manualmente;
- depender exclusivamente de uma ação que exige uma janela de horário atual.

## Perguntas que podem surgir

### Por que usar três perfis?

Porque cada pessoa toma decisões diferentes sobre o mesmo registro: o Usuário
usa um computador, o Monitor opera a sala e o Supervisor analisa e configura a
operação. Separar papéis reduz ações indevidas e torna a interface mais direta.

### Como o sistema evita dois usos no mesmo computador?

As regras são validadas em serviços transacionais e constraints do PostgreSQL
protegem invariantes persistentes. A interface não é a fonte de verdade para
conflitos ou disponibilidade.

### Por que uma sessão pode ter mais de um computador?

Uma troca não deve apagar o caminho percorrido pela pessoa. A sessão representa
o uso contínuo; as alocações registram cada computador e cada intervalo.

### Como os relatórios continuam confiáveis?

Eles são projeções sobre fatos operacionais registrados. O cálculo considera
calendário, disponibilidade histórica e alocações reais; quando o histórico de
estado de um computador é incoerente, o sistema o exclui daquela métrica e
apresenta um aviso.

### Por que não há integração institucional?

O MVP já autentica contas locais por CPF ou matrícula e senha. Ainda não há
integração com identidade institucional, autocadastro ou uso de dados reais;
essas etapas exigem provisionamento, segurança e decisões próprias.

## Checklist de ensaio

- [ ] preencher nomes, orientador e dados institucionais da capa;
- [ ] cronometrar a apresentação duas vezes sem interromper;
- [ ] confirmar que a parte inicial dura no máximo cinco minutos;
- [ ] testar todos os perfis e páginas escolhidos para a demo;
- [ ] reproduzir os dois vídeos no computador e projetor finais;
- [ ] manter a aplicação, a aba de relatórios e os vídeos abertos antes de
      começar;
- [ ] levar carregador, adaptador de vídeo e cópia local dos arquivos;
- [ ] ensaiar uma versão curta de dez minutos caso o tempo seja reduzido;
- [ ] encerrar repetindo problema, solução e resultado, sem abrir uma nova
      tela.

## Fontes para montar os slides

- [Visão geral do produto](../product/00-visao-geral.md)
- [Atores e permissões](../product/02-atores-e-permissoes.md)
- [Regras de negócio](../product/03-regras-de-negocio.md)
- [Visão geral da arquitetura](../architecture/00-visao-geral.md)
- [Modelo de domínio](../architecture/02-modelo-de-dominio.md)
- [Relatórios](../architecture/06-relatorios.md)
- [Estado da implementação](../architecture/08-estado-implementacao.md)
- [Diagramas](../diagrams/README.md)
- [Protótipo](../../prototipos/README.md)
