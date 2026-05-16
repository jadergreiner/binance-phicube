## Why

A tomada de decisão operacional exige leitura rápida de assertividade por símbolo e janela temporal, algo que hoje não está consolidado no dashboard. Sem essa visão, decisões de alocação e ajuste de risco ficam lentas e sujeitas a interpretação manual.

## What Changes

- Adicionar uma capacidade de análise de assertividade por símbolo e período no dashboard/API.
- Introduzir filtros de período (`7d`, `30d`, `90d`, `custom`) e filtros por símbolo/timeframe para consulta das métricas.
- Expor ranking por símbolo com indicadores operacionais (assertividade, PnL, profit factor, drawdown, sinais e trades).
- Expor série temporal agregada de assertividade para acompanhamento de evolução no período.
- Ajustar a capacidade existente de métricas para incluir taxa de conversão de sinal em trade e novos agregados por período.
- Estruturar a solução com design patterns explícitos: `Strategy` (janelas/períodos), `Facade` (orquestração do endpoint), `Repository` (consulta/extração de dados) e `DTO/Adapter` (contratos de resposta).

## Capabilities

### New Capabilities
- `model-assertiveness-dashboard`: Visão e contratos de assertividade por símbolo/período para dashboard e API.

### Modified Capabilities
- `performance-metrics-unification`: Amplia requisitos para agregações orientadas a período/símbolo e métricas de conversão de sinais.

## Impact

- Backend: novas rotas/serviços de agregação de métricas para dashboard.
- Frontend: novos filtros e seções de resumo, ranking por símbolo e evolução temporal.
- Testes: cobertura de cálculo, filtros de período e contratos de resposta.
- Operação: melhora de observabilidade gerencial para decisão de risco e priorização de símbolos.
