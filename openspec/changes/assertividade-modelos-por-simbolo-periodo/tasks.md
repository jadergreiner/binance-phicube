## 1. Backend API de Assertividade

- [x] 1.1 Definir contrato de endpoint de assertividade com filtros `symbol`, `timeframe`, `period`, `start`, `end`
- [x] 1.2 Implementar `Strategy` de período (`7d`, `30d`, `90d`, `custom`) com normalização temporal
- [x] 1.3 Implementar agregação por símbolo com métricas `assertiveness_pct`, `total_signals`, `total_trades`, `signal_to_trade_conversion_pct`, `pnl_usdt`, `profit_factor`, `max_drawdown_usdt`
- [x] 1.4 Implementar ordenação de ranking por `assertiveness_pct` e `pnl_usdt`
- [x] 1.5 Implementar série temporal por bucket (diário/semanal) para evolução de assertividade

## 2. Integração com Núcleo de Métricas

- [x] 2.1 Implementar `Facade` da assertividade para orquestrar repositório, core de métricas e montagem de resposta
- [x] 2.2 Definir DTOs e adapter de saída para resumo, ranking e série temporal
- [x] 2.3 Reutilizar `performance-metrics-unification` nos cálculos de assertividade
- [x] 2.4 Adicionar cálculo padronizado de conversão sinal->trade com proteção para divisão por zero
- [x] 2.5 Garantir consistência semântica entre métricas globais e métricas por símbolo/período

## 3. Frontend Canônico (:8080)

- [x] 3.1 Adicionar seção "Assertividade dos Modelos" com filtros por símbolo, timeframe e período
- [x] 3.2 Implementar cards de resumo do período selecionado
- [x] 3.3 Implementar tabela de ranking por símbolo com ordenação
- [x] 3.4 Implementar visualização da evolução temporal em tabela
- [x] 3.5 Persistir e restaurar preferências de filtros na UI

## 4. Qualidade e Validação

- [x] 4.1 Criar testes de API para filtros, contratos e ordenação da nova visão
- [x] 4.2 Criar testes de cálculo de assertividade/conversão/drawdown com fixtures controladas
- [x] 4.3 Atualizar testes de frontend para presença de filtros, seções e consumo dos endpoints
- [x] 4.4 Executar `ruff check src/ tests/` e suíte focada do dashboard
- [x] 4.5 Executar `openspec validate --strict --type change assertividade-modelos-por-simbolo-periodo`
