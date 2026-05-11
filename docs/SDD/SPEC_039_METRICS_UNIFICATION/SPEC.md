# SPEC_039 — Unificação de `_calc_metrics` em `common/metrics.py`

**ID:** SPEC_039
**Status:** Rascunho
**Data:** 2026-05-11
**Versão:** 1.0
**Dependências:** Nenhuma
**Skill de validação:** `sdd-spec-driven-development`, `qa-review`

---

## 1. Título e Resumo

### 1.1 Nome da Funcionalidade

Módulo centralizado de cálculo de métricas de performance

### 1.2 Resumo

**O que é:** Extração da lógica de cálculo de métricas (win rate, PnL total, profit factor, max drawdown) do `BacktestEngine` e `MongoRepository` para um módulo `common/metrics.py` com interface única baseada em protocolo.

**Por que estamos fazendo:** Atualmente `_calc_metrics` existe em duas implementações independentes: `repository.py:44` (opera sobre `list[dict]`) e `backtest/engine.py:373` (opera sobre `list[BacktestTrade]`). A lógica é idêntica, mas as estruturas diferem. Qualquer correção em uma precisa ser replicada na outra.

**Valor de negócio:** Elimina duplicação, garante consistência nas métricas entre backtest e produção, facilita adição de novas métricas (Sharpe, Sortino, etc.), reduz superfície de bugs.

**Conexão com PRD/SPEC:** `SPEC_006` (relatório de performance), `SPEC_028` (backtest realista).

---

## 2. Objetivos e Escopo

### 2.1 Objetivos

- [ ] Criar `common/metrics.py` com função `compute_metrics(trades: Sequence[HasPnL]) -> Metrics`
- [ ] Definir protocolo `HasPnL` para compatibilidade entre BacktestTrade e dicionários
- [ ] Refatorar `repository.py` e `backtest/engine.py` para usar o novo módulo
- [ ] Adicionar testes unitários para `compute_metrics`

### 2.2 Fora do Escopo

- **Não inclui:** Cálculo de Sharpe Ratio, Sortino, Calmar — pode ser adicionado depois
- **Não inclui:** Mudança no schema do MongoDB ou formato de relatório
- **Não inclui:** Mudança na API dos endpoints de performance

---

## 3. Referências

| Documento | Seção | Relevância |
|---|---|---|
| `src/storage/repository.py` | `_calc_metrics()` linha 44 | Código alvo da refatoração |
| `src/backtest/engine.py` | `_calc_metrics()` linha 373 | Código alvo da refatoração |
| `src/backtest/engine.py` | `_build_result()` linha 415 | Consumidor secundário |
| `SPEC_006/SPEC.md` | — | Métricas de performance |
| `SPEC_028/SPEC.md` | — | Backtest realista |

---

## 4. Histórias de Usuário e Requisitos

### US-039-01: Protocolo `HasPnL` e dataclass `Metrics`

> Como **desenvolvedor**, quero **um protocolo `HasPnL` que abstraia tanto `BacktestTrade` quanto `dict` de trade** para **poder usar a mesma função de métricas em contextos diferentes**.

```python
class HasPnL(Protocol):
    pnl_usdt: float

@dataclass(frozen=True)
class Metrics:
    total_trades: int
    win_rate_pct: float
    total_pnl_usdt: float
    avg_rrr: float
    max_drawdown_usdt: float
    profit_factor: float
```

- [ ] AC-01: `HasPnL` é compatível com `BacktestTrade` sem adaptador
- [ ] AC-02: `HasPnL` é compatível com dict via classe adaptadora

### US-039-02: Função `compute_metrics`

> Como **desenvolvedor**, quero **`compute_metrics(trades, pnl_field="pnl_usdt")` que aceita qualquer sequência de trades** para **substituir ambas as implementações de `_calc_metrics`**.

```text
DADO   uma lista de BacktestTrade com 5 wins e 3 losses
QUANDO compute_metrics(trades) é chamado
ENTÃO  win_rate_pct == 62.5 e profit_factor > 0
```

- [ ] AC-01: Win rate calculado corretamente para casos com 0 wins
- [ ] AC-02: Win rate calculado corretamente para casos com 0 trades
- [ ] AC-03: Max drawdown calculado corretamente sobre equity acumulada
- [ ] AC-04: Profit factor = infinity quando gross_loss == 0

---

## 5. Design e Arquitetura

### 5.1 Módulo `common/metrics.py`

```python
from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


class HasPnL(Protocol):
    """Protocolo para qualquer objeto que tenha pnl_usdt."""
    pnl_usdt: float


@dataclass(frozen=True)
class Metrics:
    total_trades: int
    win_rate_pct: float
    total_pnl_usdt: float
    avg_rrr: float
    max_drawdown_usdt: float
    profit_factor: float


def compute_metrics(
    trades: Sequence[HasPnL],
    pnl_field: str = "pnl_usdt",
) -> Metrics:
    """Calcula métricas de performance sobre uma sequência de trades.

    Args:
        trades: Sequência de objetos com atributo pnl_field (float).
        pnl_field: Nome do campo de PnL a usar.

    Returns:
        Metrics com win rate, total PnL, avg RRR, drawdown e profit factor.
    """
    if not trades:
        return Metrics(...)

    # win rate, total pnl, avg rrr, max drawdown, profit factor
    ...
```

### 5.2 Adaptador para dict

```python
@dataclass
class DictTradeAdapter:
    data: dict
    pnl_field: str = "pnl_usdt"

    @property
    def pnl_usdt(self) -> float:
        return self.data.get(self.pnl_field, 0.0)
```

### 5.3 Arquivos Afetados

| Arquivo | Mudança |
|---|---|
| `src/common/metrics.py` | **Novo** — módulo central |
| `src/storage/repository.py` | Substituir `_calc_metrics` por `compute_metrics` |
| `src/backtest/engine.py` | Substituir `_calc_metrics` por `compute_metrics` |
| `tests/common/test_metrics.py` | **Novo** — testes do módulo |

---

## 6. Regras de Negócio e Restrições

### 6.1 Invariantes

| ID | Invariante | Violação → Ação |
|---|---|---|
| INV-039-01 | `len(trades) == total_trades` | Bugs em construção de Metrics |
| INV-039-02 | `win_rate_pct` entre 0 e 100 | Clamping se necessário |
| INV-039-03 | `profit_factor` nunca é negativo | Se ambos gross_profit e gross_loss forem 0, retorna 0.0 |

---

## 7. Testes e Validação

### 7.1 Testes Unitários

| ID | Descrição | Cenário |
|---|---|---|
| TEST-039-01 | Lista vazia → Metrics com zeros | `compute_metrics([])` |
| TEST-039-02 | Trades alternados → profit factor correto | 3 trades: win, loss, win |
| TEST-039-03 | Drawdown calculado corretamente | Sequência: +100, -200, +50 |
| TEST-039-04 | `pnl_field` customizado → usa campo alternativo | BacktestTrade.pnl_gross_usdt |
| TEST-039-05 | Compatibilidade com dict via DictTradeAdapter | DictTradeAdapter({"pnl_usdt": 10.0}).pnl_usdt == 10.0 |

### 7.2 Evidências Requeridas na PR

- [ ] `pytest tests/common/test_metrics.py` passando
- [ ] Backtest tests existentes passando sem alteração
- [ ] Repository tests existentes passando sem alteração

---

## 8. Riscos e Mitigações

| Risco | Impacto | Mitigação |
|---|---|---|
| BacktestTrade precisa de adaptador extra | Baixo | HasPnL é compatível diretamente |
| Cálculo de metrics difere entre backtest e produção | Médio | Testes comparam output antigo vs novo no mesmo dataset |

---

## 9. Definição de Pronto (DoD)

- [ ] `common/metrics.py` criado com `HasPnL`, `Metrics`, `compute_metrics`
- [ ] `repository.py` usa `compute_metrics`
- [ ] `backtest/engine.py` usa `compute_metrics`
- [ ] Testes existentes passam (backtest + repository)
- [ ] Cobertura do novo módulo ≥ 95%

---

## Histórico

- **2026-05-11:** Criação da SPEC_039.
