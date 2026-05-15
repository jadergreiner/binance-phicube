## Context

Atualmente, o cálculo de métricas de performance está fragmentado em três pontos:

- `MongoRepository._calc_metrics` para trades persistidos como `dict`;
- `BacktestEngine._calc_metrics` para `list[BacktestTrade]`;
- trecho de métricas em `BacktestEngine._build_result` com `pnl_field` dinâmico.

Esses caminhos compartilham intenção, mas diferem em detalhes de entrada e ordenação. A mudança é cross-cutting entre storage e backtest e precisa preservar contratos já exercitados pelos testes existentes.

## Goals / Non-Goals

**Goals:**
- Centralizar a matemática de métricas em um núcleo único e determinístico.
- Permitir reuso do núcleo para `pnl_usdt`, `pnl_gross_usdt` e `pnl_net_usdt`.
- Preservar semântica operacional atual:
  - `profit_factor = 0.0` quando `gross_loss == 0`;
  - `max_drawdown_usdt <= 0.0`.
- Reduzir risco de drift entre produção e backtest.

**Non-Goals:**
- Introduzir novas métricas (Sharpe, Sortino, Calmar).
- Alterar payload de API, schema de banco, ou estrutura pública de `BacktestResult`.
- Mudar regras de trading, execução ou persistência de trades.

## Decisions

### 1) Núcleo de métricas orientado a dados numéricos
**Decisão:** criar função comum que receba sequências numéricas já extraídas (`pnls`, `rrrs`) e devolva um resultado de métricas padronizado.

**Racional:** reduz acoplamento a tipos de domínio (`dict` vs dataclass) e elimina necessidade de adaptadores complexos por protocolo dinâmico.

**Alternativas consideradas:**
- `Protocol HasPnL` + adaptadores: melhora tipagem OO, mas complica suporte natural a `pnl_field` dinâmico.
- Manter duplicação: menor esforço imediato, maior custo de manutenção e risco de inconsistência.

### 2) Extração por borda de contexto
**Decisão:** cada consumidor mantém apenas a extração dos dados de origem:
- repository extrai `pnls/rrrs` com ordenação por `closed_at`;
- backtest extrai `pnls/rrrs` em ordem de execução e respeita `pnl_field`.

**Racional:** preserva regras contextuais locais e centraliza apenas a matemática comum.

**Alternativas consideradas:**
- mover toda a lógica para um único adaptador universal de trade; aumenta complexidade sem ganho proporcional.

### 3) Unificar também métricas de `_build_result`
**Decisão:** aplicar o mesmo núcleo ao caminho de métricas usado em `_build_result`.

**Racional:** sem isso, a unificação ficaria incompleta e a principal fonte de drift no backtest permaneceria.

### 4) Preservar contratos semânticos atuais
**Decisão:** manter:
- `profit_factor = 0.0` quando sem perdas;
- drawdown como valor não-positivo (0 ou negativo);
- arredondamentos compatíveis com comportamento atual.

**Racional:** evita quebra de testes, dashboards e comparabilidade histórica.

## Risks / Trade-offs

- [Mudança semântica acidental em drawdown/profit_factor] -> Validar com testes de regressão existentes e cenários unitários determinísticos.
- [Diferença de ordenação entre produção e backtest] -> Manter ordenação explícita por contexto antes da chamada ao núcleo.
- [Escopo crescer para novas métricas] -> Congelar escopo desta mudança nas 6 métricas atuais.
- [Acoplamento indevido do núcleo a estruturas de domínio] -> Garantir assinatura orientada a sequências numéricas simples.

## Migration Plan

1. Introduzir núcleo comum de métricas.
2. Migrar `MongoRepository._calc_metrics` para usar o núcleo.
3. Migrar `BacktestEngine._calc_metrics` e `_build_result` para usar o mesmo núcleo.
4. Executar testes de storage e backtest para confirmar paridade comportamental.
5. Remover lógica duplicada residual.

Rollback:
- Reverter apenas a integração dos consumidores para a implementação anterior, mantendo o núcleo comum isolado sem uso se necessário.

## Open Questions

- O núcleo retorna `dict` ou dataclass interna de métricas antes do mapeamento final?
- A ordenação por tempo deve ser responsabilidade explícita sempre do chamador, sem fallback no núcleo?
