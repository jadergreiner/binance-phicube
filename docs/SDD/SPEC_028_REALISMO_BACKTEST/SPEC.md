# SPEC_028 — Realismo em Backtest: Slippage e Taxas

**ID:** SPEC_028
**Título:** Realismo em Backtest: Slippage e Taxas
**Data:** 2026-05-10
**Status:** Rascunho
**Versão:** 1.0
**Dependências:** SPEC_011 (Motor de Backtesting)
**PRD §:** Fase 2 — "Backtests e walk-forward analysis"

---

## 1. Objetivo

Adicionar slippage variável e taxas Binance (maker/taker) ao `BacktestEngine` para que os resultados de backtest reflitam condições reais de mercado, eliminando o viés otimista do modelo atual.

O motor hoje assume entrada/saída no close exato do candle sem custos — resultado sempre melhor que a realidade.

---

## 2. Escopo

### Dentro do escopo
- Modelo de slippage flat (USDT) + percentual configurável por par
- Taxas Binance: 0.02% maker / 0.05% taker (padrão VIP 0), configuráveis
- Slippage aplicado na entrada (market) e saída (SL/TP hit via stop order)
- Flag `--realistic` no CLI e `realistic=true` na API para ativar/desativar
- Resultado exibido com e sem custos para comparação

### Fora do escopo
- Slippage por profundidade de livro de ofertas (order book)
- Taxas diferenciadas por nível VIP por conta
- Slippage por volatilidade intrabar

---

## 3. User Stories

### US-028-01 — Execução realista no CLI
**Como** operador,
**quero** executar `python -m src.backtest.runner --symbol BTCUSDT --timeframe 4h --realistic`,
**para** ver métricas com slippage e taxas incluídas.

**Critério de aceite:**
- Saída exibe colunas extras: `total_fees`, `total_slippage`
- Resultado realista tem PnL menor ou igual ao sem custos

### US-028-02 — Comparação lado a lado
**Como** operador,
**quero** ver `BacktestResult` com e sem custos na mesma execução,
**para** entender o impacto realista da estratégia.

**Critério de aceite:**
- `BacktestResult` inclui `realistic: bool` e sub-campos `gross`/`net`

---

## 4. Modelo de Dados

### Extensões em `BacktestTrade`

| Campo | Tipo   | Descrição                               |
|-------|--------|-----------------------------------------|
| `entry_fee` | `float` | Taxa paga na entrada (USDT)       |
| `exit_fee` | `float`  | Taxa paga na saída (USDT)         |
| `slippage_entry` | `float` | Deslize no preço de entrada (USDT) |
| `slippage_exit` | `float`  | Deslize no preço de saída (USDT)   |
| `pnl_net_usdt` | `float`  | PnL líquido (deduzindo taxas + slippage) |

### Extensões em `BacktestResult`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `gross` | `BacktestResult` | Resultado sem custos (comportamento atual) |
| `net` | `BacktestResult` | Resultado com custos |
| `total_fees_usdt` | `float` | Soma total de taxas |
| `total_slippage_usdt` | `float` | Soma total de slippage |

---

## 5. Componentes

### 5.1 Configuração (`src/config/settings.py` — extensão)

```python
# Novos campos em Settings
BACKTEST_SLIPPAGE_FLAT: float = 0.5       # USDT por ordem
BACKTEST_SLIPPAGE_PCT: float = 0.0         # % adicional (ex.: 0.01 = 0.01%)
BACKTEST_MAKER_FEE: float = 0.0002         # 0.02%
BACKTEST_TAKER_FEE: float = 0.0005         # 0.05%
```

### 5.2 BacktestEngine — novo método `_apply_costs`

```python
def _apply_costs(
    self,
    price: float,
    trade_type: Literal["entry", "exit"],
    order_type: Literal["market", "stop"],
) -> tuple[float, float, float]:
    """Aplica slippage e taxa no preço dado.

    Returns:
        (price_with_slippage, fee_amount, slippage_amount)
    """
```

**Algoritmo:**
1. Slippage = `slippage_flat + price * slippage_pct`
2. Preço ajustado: LONG entry sofre +slippage, SHORT entry sofre −slippage
3. Taxa = `price_adjusted * (maker_fee se stop, taker_fee se market)`
4. PnL líquido: `pnl_gross - entry_fee - exit_fee`

### 5.3 Runner CLI — flag `--realistic`

```
python -m src.backtest.runner --symbol BTCUSDT --timeframe 4h --realistic
```

### 5.4 API — query param `realistic`

```
GET /backtest?symbol=BTCUSDT&timeframe=4h&realistic=true
```

---

## 6. Invariantes

| ID | Invariante |
|----|-----------|
| INV-028-01 | `pnl_net_usdt` nunca é maior que `pnl_usdt` para o mesmo trade |
| INV-028-02 | Slippage mínimo = 0.0 (configurável para zero) |
| INV-028-03 | Taxa nunca excede o valor da posição (max 100%) |
| INV-028-04 | `--realistic` não altera trades gerados — só os custos |

---

## 7. Testes

| ID | Descrição |
|----|-----------|
| TEST_028_01 | Trade long realistic: entry_price sobe com slippage, PnL líquido < bruto |
| TEST_028_02 | Trade short realistic: entry_price desce com slippage, PnL líquido < bruto |
| TEST_028_03 | Slippage = 0 → PnL líquido = bruto − taxas |
| TEST_028_04 | realistic=false → mesmo comportamento de antes (sem custos) |
| TEST_028_05 | API com realistic=true retorna campos gross/net distintos |

---

## 8. Arquivos

| Arquivo | Mudança |
|---------|---------|
| `src/config/settings.py` | Modificado — novos campos `BACKTEST_SLIPPAGE_*`, `BACKTEST_FEE_*` |
| `src/backtest/engine.py` | Modificado — `_apply_costs`, `BacktestResult` com gross/net |
| `src/backtest/models.py` | Modificado — novos campos `BacktestTrade`, `BacktestResult` |
| `src/backtest/runner.py` | Modificado — flag `--realistic` |
| `src/api/routes/backtest.py` | Modificado — query param `realistic` |
| `tests/backtest/test_realistic.py` | Criado — TEST_028_01 a 05 |

---

## 9. Definition of Done

- [ ] `_apply_costs` implementado com INV-028-01 a 04
- [ ] CLI `--realistic` funcional com saída distinta
- [ ] API `GET /backtest?realistic=true` retornando gross/net
- [ ] TEST_028_01 a 05 passando
- [ ] `ruff check src/ tests/` limpo nos arquivos alterados
