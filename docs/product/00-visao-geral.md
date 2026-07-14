# Visão geral do produto

## Problema

O uso da Sala de Informática da Biblioteca da UFAC é registrado manualmente em folhas impressas. Depois, os dados precisam ser consolidados em relatórios diários, semanais, mensais e anuais. Esse processo produz retrabalho, dificulta consultas históricas e aumenta o risco de erros.

## Objetivo

Construir um sistema web para registrar, acompanhar e analisar o uso dos computadores da sala, permitindo que o próprio usuário consulte disponibilidade, reserve para o dia seguinte, registre entrada e saída, troque de computador e informe problemas.

## Resultados esperados

- substituir o registro manual de entrada e saída;
- manter histórico confiável de sessões e computadores utilizados;
- controlar o estado operacional dos computadores;
- evitar conflitos de uso e reservas;
- gerar relatórios a partir dos registros reais;
- permitir acompanhamento operacional pelo Estagiário;
- permitir análise gerencial pelo Supervisor;
- manter base arquitetural para futura administração de contas, permissões, parâmetros e logs.

## Atores

- Usuário da Sala: aluno, professor ou técnico-administrativo que utiliza os computadores.
- Estagiário: acompanha a operação diária, corrige registros, trata ocorrências e gera relatórios operacionais.
- Supervisor da Biblioteca: configura dados institucionais, acompanha indicadores e gera relatórios consolidados.
- Administrador do Sistema: papel arquitetural responsável futuramente por contas, permissões, parâmetros e auditoria.

## Restrições atuais

- não existe fila de espera;
- consulta limitada a hoje e amanhã;
- uso imediato somente hoje e em horários ainda não passados;
- reserva antecipada somente amanhã;
- autenticação real fora do MVP inicial;
- integração com autenticação institucional fora do escopo;
- Técnico de Manutenção/TI não é ator nesta etapa;
- relatórios não possuem lançamentos próprios.

## Princípio central do domínio

O sistema registra eventos reais de uso. Sessões, alocações, reservas, ocorrências e turnos formam a base dos relatórios. A interface não deve permitir criar totais de relatório desconectados desses registros.
