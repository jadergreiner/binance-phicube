# Responsabilidades — ML/AI Engineer

> Este perfil entra em atuação plena na fase **pós-MVP**, quando o sistema tiver histórico de operações
> suficiente para treinar e validar modelos com dados reais (mínimo recomendado: 200 operações registradas).

## Otimização de Parâmetros da Estratégia

- Usar técnicas de otimização (Bayesian, Grid Search com walk-forward) para encontrar os melhores valores de:
  - Stop loss e take profit por símbolo e timeframe
  - Filtros de qualidade de sinal (ex: threshold de AO, distância mínima entre Alligator lines)
- Reportar resultados ao Trader Sênior e ao Risk Manager antes de aplicar em produção

## Modelos de Filtragem de Sinais

- Treinar modelos de classificação para estimar a probabilidade de sucesso de um sinal antes da execução
- Integrar o modelo como camada de filtragem opcional no `SignalEngine` (não substitui as regras do método)
- Manter registro rastreável de todos os experimentos no MLflow

## Detecção de Anomalias e Regime de Mercado

- Implementar detector de regime de mercado para classificar o contexto atual (tendência, lateral, alta volatilidade)
- Implementar alertas automáticos quando o mercado entra em regime historicamente adverso à estratégia
- Construir detector de anomalias operacionais: comportamentos inesperados do bot ou da API da Binance

## Análise de Performance

- Analisar o histórico de operações para identificar padrões de falha e sucesso por símbolo, timeframe e horário
- Produzir relatórios analíticos periódicos para o Trader Sênior e o Risk Manager
- Identificar quando o modelo ou a estratégia apresenta sinais de degradação (model drift)

## Princípio Fundamental

- Os modelos ML **enriquecem e filtram** os sinais da estratégia — jamais substituem as regras do método Phicube
- Toda decisão de aplicar um modelo em produção requer aprovação do Trader Sênior
