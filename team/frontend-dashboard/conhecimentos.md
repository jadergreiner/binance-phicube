# Conhecimentos Específicos — Frontend Dashboard

## Visualização de Dados Financeiros

- Gráficos de candlestick (OHLCV) com sobreposição de indicadores (Alligator, AO)
- TradingView Lightweight Charts ou similar para visualização de candles em tempo real
- Tabelas de operações com filtros, ordenação e paginação
- Gráficos de P&L acumulado, drawdown e equity curve
- Heatmaps e métricas de performance por símbolo e timeframe

## Atualização em Tempo Real

- WebSocket no frontend para consumir atualizações de sinal e status de operações
- Server-Sent Events (SSE) como alternativa mais simples para notificações
- Gerenciamento de estado reativo: React Query, Zustand, Pinia ou similar
- Tratamento de reconexão automática em caso de queda do WebSocket

## Interface e UX

- Design responsivo: o trader pode monitorar no celular durante o dia
- Feedback visual claro para estados do sistema: bot ativo, parado, erro, operação aberta
- Notificações no browser (Web Notifications API) para alertas de sinal detectado ou operação executada
- Acessibilidade básica: contraste adequado, fontes legíveis em telas financeiras

## Integração com Backend

- Consumo de API REST para listagem de trades, sinais e métricas
- Autenticação básica para acesso ao dashboard (não exposto publicamente)
- Paginação e filtros por período, símbolo e status
