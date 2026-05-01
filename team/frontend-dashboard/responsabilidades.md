# Responsabilidades — Frontend Dashboard

## Telas Principais do Dashboard

Projetar e implementar as seguintes telas:

- **Visão Geral**: status do bot (ativo/parado), saldo disponível, posições abertas, P&L do dia
- **Operações**: tabela de trades abertos e histórico com filtros por símbolo, período e status
- **Sinais**: lista de sinais detectados (executados e não executados) com entrada, SL, TP e direção
- **Performance**: equity curve, drawdown, win rate, profit factor por período
- **Configurações**: exibição dos parâmetros ativos (read-only no MVP; editável futuramente)

## Experiência do Trader

- Garantir que as informações mais críticas (posições abertas, saldo, alertas) estejam visíveis sem scroll
- Implementar indicador visual de saúde do sistema: verde (operando), amarelo (atenção), vermelho (erro/parado)
- Notificações no browser para eventos: sinal detectado, operação aberta, stop loss acionado, take profit atingido

## Colaboração

- Trabalhar com o Trader Sênior para validar a prioridade e o layout das informações
- Consumir as APIs expostas pelo Backend Sênior para listagem de trades e sinais
- Trabalhar com o DevOps para deploy do dashboard no mesmo ambiente Docker do bot

## Qualidade

- Garantir que o dashboard funcione em Chrome, Firefox e Safari (desktop e mobile)
- Evitar dependências pesadas desnecessárias — o dashboard deve carregar rápido
- Implementar tratamento de erro visual quando a API estiver indisponível
