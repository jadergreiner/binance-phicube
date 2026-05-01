# Responsabilidades — Trader Sênior Phicube

## Autoridade no Método

- Ser a **referência definitiva** sobre as regras da estratégia BO Williams Phicube
- Documentar as regras de entrada, saída, stop loss e take profit de forma objetiva e sem ambiguidade
- Aprovar ou reprovar qualquer alteração na lógica de detecção de sinais implementada pelo Quant Developer

## Validação e Testes

- Revisar e validar os resultados de backtesting produzidos pelo Quant Developer
- Executar operações manuais paralelas em ambiente de teste para comparar com as decisões do sistema
- Sinalizar divergências entre o comportamento do bot e o comportamento esperado da estratégia

## Interface com a Equipe

- Participar das cerimônias de refinamento de backlog com o Product Owner
- Explicar as regras da estratégia para o Quant Developer e o ML/AI Engineer em linguagem técnica
- Ser o responsável pela decisão final de **ligar ou desligar** o bot em produção

## Monitoramento Contínuo

- Acompanhar o histórico de operações no dashboard e identificar padrões de degradação
- Sinalizar quando o mercado está em regime adverso à estratégia (ex: lateralidade extrema)
- Definir critérios de pausa automática do sistema por drawdown excessivo
