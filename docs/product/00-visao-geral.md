# Visão geral do produto

## Problema

O uso da Sala de Informática da Biblioteca da UFAC é registrado manualmente. A consolidação posterior em relatórios causa retrabalho, dificulta consultas históricas e aumenta o risco de erro.

## Objetivo

Construir um sistema web para registrar, acompanhar e analisar o uso dos computadores. O próprio usuário poderá consultar disponibilidade, reservar horário futuro de hoje ou de amanhã, registrar entrada e saída, trocar de computador e informar problemas.

## Resultados esperados

- substituir o registro manual de entrada e saída;
- manter histórico de sessões e computadores utilizados;
- controlar o estado operacional dos computadores;
- evitar conflitos de uso e reservas;
- gerar relatórios a partir dos registros reais;
- permitir acompanhamento operacional pelo Estagiário;
- permitir análise gerencial pelo Supervisor;
- manter base para futura administração de contas, permissões, parâmetros e logs.

## Atores

- **Usuário da Sala:** aluno, professor ou técnico-administrativo.
- **Estagiário:** acompanha operação, corrige registros, trata ocorrências e gera relatórios operacionais.
- **Supervisor da Biblioteca:** configura dados, acompanha indicadores e gera relatórios consolidados.
- **Administrador do Sistema:** papel arquitetural futuro para contas, permissões, parâmetros e auditoria.

## Restrições atuais

- sem fila de espera;
- consulta limitada a hoje e amanhã;
- uso imediato somente hoje;
- reservas para horário futuro de hoje ou para amanhã;
- sem autenticação real;
- sem integração institucional;
- sem ator Técnico de Manutenção/TI;
- sem lançamentos manuais de relatório.

## Princípio central

Sessões, alocações, reservas, ocorrências, turnos e histórico operacional formam a base dos relatórios. Nenhum total deve ser lançado de forma desconectada desses registros.
