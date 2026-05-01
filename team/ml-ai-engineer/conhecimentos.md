# Conhecimentos Específicos — ML/AI Engineer

## Machine Learning para Séries Temporais

- Modelos de classificação para previsão de direção: XGBoost, LightGBM, Random Forest
- Redes neurais para séries temporais: LSTM, GRU, Temporal Convolutional Networks (TCN)
- Técnicas de validação temporal: walk-forward analysis, purged k-fold cross-validation
- Feature engineering para dados OHLCV: lags, rolling statistics, indicadores derivados
- Prevenção de data leakage em pipelines de séries temporais

## Otimização de Parâmetros

- Bayesian Optimization para hiperparâmetros de estratégias (Optuna, Hyperopt)
- Grid Search e Random Search com validação temporal adequada
- Avaliação de robustez: teste de sensibilidade a variações nos parâmetros

## MLOps e Rastreamento de Experimentos

- MLflow: rastreamento de runs, métricas, artefatos e modelos
- Versionamento de datasets e modelos
- Pipelines de retreinamento periódico com novos dados
- Monitoramento de drift de modelo em produção

## Análise e Features Externas

- Análise de sentimento de notícias e redes sociais (NLP básico aplicado a crypto)
- Dados on-chain como features: exchange inflows/outflows, whale alerts
- Fear & Greed Index e correlação com regime de mercado
- Correlação entre ativos (BTC dominance, ETH/BTC ratio) como features contextuais

## Detecção de Anomalias

- Isolation Forest, Autoencoders para detecção de comportamento anômalo do mercado
- Identificação de regimes de mercado: clustering (K-Means, HMM) aplicado a retornos
