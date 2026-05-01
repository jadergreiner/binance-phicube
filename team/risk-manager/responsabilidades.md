# Responsabilidades — Risk Manager

## Definição dos Parâmetros de Risco

- Definir e documentar os parâmetros configuráveis de risco do sistema:
  - Percentual máximo de risco por operação (`RISK_PER_TRADE_PCT`)
  - Relação risco/retorno mínima (`RISK_REWARD_RATIO`)
  - Capital máximo alocado simultaneamente (`MAX_CAPITAL_ALLOCATION_PCT`)
  - Número máximo de posições abertas (`MAX_OPEN_POSITIONS`)
  - Alavancagem por símbolo (`LEVERAGE`)
- Justificar cada parâmetro com base em dados históricos da estratégia

## Circuit Breakers

- Definir as regras de pausa automática do sistema:
  - Drawdown diário máximo tolerado
  - Drawdown mensal máximo antes de intervenção manual obrigatória
  - Condições de mercado que justificam desligar o bot manualmente
- Validar com o Backend Sênior a implementação técnica dos circuit breakers

## Revisão Periódica

- Revisar mensalmente os parâmetros de risco com base no desempenho real
- Produzir relatório de risco mensal: drawdown, expectativa, eficiência da gestão
- Propor ajustes de parâmetros ao Product Owner quando os dados indicarem necessidade

## Interface com o Time

- Alinhar com o Trader Sênior os critérios de pausa manual do bot
- Validar com o ML/AI Engineer os limites de risco dos modelos pós-MVP
- Ser consultado antes de qualquer alteração nos parâmetros de risco em produção
