# SPEC_029 — Position Sizing por ATR

**ID:** SPEC_029
**Título:** Position Sizing por ATR
**Data:** 2026-05-11
**Status:** Concluída
**Versão:** 2.0
**Dependências:** SPEC_006 (métricas), SPEC_022 (convergência risco)
**PRD §:** Fase 2 — "Gestão de risco dinâmica"

---

## 1. Objetivo

Substituir o position sizing fixo (`risk_per_trade_pct` % do saldo) por um modelo dinâmico baseado em ATR (Average True Range) que mantém **risco constante em USDT por trade**, independente da volatilidade do par — com proteção contra superdimensionamento via `effective_stop = max(fractal_sl_distance, atr_value * atr_multiplier)`.

Sizing mode: `"atr"` (SizingMode.ATR). O guard `effective_stop = max(...)` é uma propriedade intrínseca do modo ATR, não um modo separado.

---

## 2. Escopo

### Dentro do escopo
- Cálculo de ATR no `indicators.py` (Wilder SMMA, período 14)
- Novo modelo de sizing: `atr` — `effective_stop = max(fractal_sl_distance, atr * atr_multiplier)`
- Risco fixo em USDT configurável (`RISK_PER_TRADE_USDT`)
- Fallback para sizing fixo se ATR indisponível (poucos candles)
- Integração com `RiskManager.calculate_position_size()`
- Flag de ativação: `SIZING_MODE = "fixed" | "atr"`
- Logging de `effective_stop` em todo cálculo de posição ATR
- Simulação de 5 pares para calibrar `atr_multiplier`

### Fora do escopo
- Sizing baseado em Kelly Criterion
- Sizing por saldo total da conta (fração de equity)
- Redução progressiva de posição em drawdown
- Sizing dinâmico por volatilidade em tempo real (usa ATR de candle fechado)

---

## 3. User Stories

### US-029-01 — Cálculo de ATR no indicators
**Como** engenheiro,
**quero** ter `indicators.atr(close, high, low, period=14)` disponível,
**para** usar no sizing e futuramente em stops dinâmicos.

**Critério de aceite:**
- Retorna `pd.Series` mesmo comprimento que entrada
- NaN nos primeiros `period` candles
- Implementação: Wilder Smoothed Moving Average (SMMA) do True Range

### US-029-02 — Sizing por ATR no RiskManager
**Como** operador,
**quero** configurar `SIZING_MODE=atr` e `RISK_PER_TRADE_USDT=5`,
**para** que cada trade arrisque exatos 5 USDT independente do par.

**Critério de aceite:**
- `SIZING_MODE=fixed` → comportamento atual (`risk_per_trade_pct` do saldo)
- `SIZING_MODE=atr` → posição = `effective_risk_per_trade_usdt * entry_price / effective_stop`
- `effective_stop = max(fractal_sl_distance, atr_value * atr_multiplier)`
- Logging de `effective_stop`, `atr_value`, `fractal_sl_distance` em todo cálculo
- Posição mínima respeitada: `MIN_POSITION_USDT`
- INV-029-05: risco real nunca ultrapassa 1.05x o configurado

---

## 4. Modelo de Dados

### RiskManager — novos campos de configuração

| Campo | Tipo | Default | Descrição |
|-------|------|---------|-----------|
| `sizing_mode` | `SizingMode` | `"fixed"` | `"fixed"` ou `"atr"` |
| `risk_per_trade_usdt` | `float` | `5.0` | Risco base por trade (USDT). Pode ser reduzido por CB pair-level + portfólio (`effective_risk_per_trade_usdt`) |
| `atr_period` | `int` | `14` | Período do ATR (Wilder) |
| `atr_multiplier` | `float` | `1.5` (env: 2.0) | Multiplicador do ATR no effective_stop |
| `min_position_usdt` | `float` | `10.0` (env: 1.0) | Posição mínima (min notional Binance) |
| `max_position_usdt` | `float` | `500.0` | Posição máxima (cap de segurança) |

### Fórmula de sizing (ATR mode)

```
# 1. ATR no mesmo timeframe do trade
atr_value = atr(close, high, low, period).iloc[-1]

# 2. Distância do SL pela regra Phicube (fractal)
fractal_sl_distance = abs(entry_price - fractal_stop_price)

# 3. Effective stop: o maior entre fractal e ATR (guarda de segurança)
effective_stop = max(fractal_sl_distance, atr_value * atr_multiplier)

# 4. Position size em USDT
position_usdt = risk_per_trade_usdt * entry_price / effective_stop

# 5. Clamp
position_usdt = clamp(position_usdt, min_position_usdt, max_position_usdt)

# 6. Quantidade do ativo
quantity = position_usdt / entry_price
quantity = round(quantity, precision)
```

---

## 5. Componentes

### 5.1 `src/strategy/indicators.py` — nova função

```python
def atr(
    close: pd.Series,
    high: pd.Series,
    low: pd.Series,
    period: int = 14,
) -> pd.Series:
    """Average True Range — Wilder's smoothed ATR (SMMA of True Range).

    Retorna pd.Series mesmo comprimento que entrada.
    NaN nos primeiros ``period`` candles.
    """
```

### 5.2 `src/trading/risk_manager.py` — método modificado

```python
class RiskManager:
    def calculate(
        self,
        signal: Signal,
        available_balance: float,
        quantity_precision: int = 3,
        intraday_realized_pnl_usdt: float = 0.0,
        now_utc: datetime | None = None,
        df: pd.DataFrame | None = None,
    ) -> PositionSize | None:
        """Retorna PositionSize ou None se violar constraints de risco.

        Se SIZING_MODE=atr e df for fornecido:
          - effective_stop = max(sl_distance, atr * mult)
          - Log: effective_stop, atr_value, fractal_sl_distance

        Se SIZING_MODE=fixed ou df=None:
          - Comportamento atual (risk_per_trade_pct do saldo)
        ```

**Algoritmo ATR (síncrono):**
1. Se `sizing_mode == "fixed"`: retorna comportamento atual
2. Se `sizing_mode == "atr"` e `df is None`: log WARN, cai para fixed
3. Se `sizing_mode == "atr"`:
   - Calcula ATR no DataFrame via `_compute_atr_value(df)` (Facade)
   - Se último ATR <= 0 → fallback para fixed
   - `effective_stop = max(fractal_sl_distance, atr_value * atr_multiplier)`
   - `position_usdt = effective_risk_per_trade_usdt * entry_price / effective_stop`
   - Aplica `max_position_pct` se configurado
   - Aplica `clamp` (min/max position)
   - Converte para quantidade do ativo
   - Valida INV-029-05: se risco real > 1.05x → rejection
   - Valida slippage gate SPEC_043: se slippage > tolerância → rejection
   - Log: `{effective_stop, atr_value, fractal_sl_distance, sizing_mode, position_usdt}`

---

## 6. Invariantes

| ID | Invariante |
|----|-----------|
| INV-029-01 | `effective_stop ≥ fractal_sl_distance` | by construction (`max()`) |
| INV-029-02 | Fallback para fixed se ATR indisponível (NaN, df=None, zero, candles insuficientes) |
| INV-029-03 | `position_usdt` clampado em [`MIN_POSITION_USDT`, `MAX_POSITION_USDT`] |
| INV-029-04 | Override de `atr_multiplier` por símbolo via `atr_multiplier_overrides` |
| INV-029-05 | Risco real `quantity * effective_stop` ≤ `effective_risk_per_trade_usdt * 1.05` |
| INV-029-06 | ATR calculado no mesmo timeframe da estratégia (df fornecido pelo TradingMonitor) |

---

## 7. Testes

| ID | Descrição | Critério |
|----|-----------|----------|
| TEST_029_01 | ATR calculado corretamente para série conhecida | Match manual vs. planilha |
| TEST_029_02 | ATR retorna NaN nos primeiros `period` candles | `assert df['atr'].isna().sum() == period` |
| TEST_029_03 | `atr_with_guard`: posição menor em alta volatilidade | ATR alto → position menor |
| TEST_029_04 | `atr_with_guard`: guard atua quando fractal > ATR | `effective_stop == fractal_sl_distance` |
| TEST_029_05 | `atr_with_guard`: ATR domina quando ATR > fractal | `effective_stop == atr * mult` |
| TEST_029_06 | Clamp respeita MIN/MAX_POSITION_USDT | `assert min <= pos <= max` |
| TEST_029_07 | Fallback para fixed quando ATR indisponível | `SIZING_MODE=atr` com df vazio → fixed |
| TEST_029_08 | INV-029-05: risco real <= 1.05x configurado | 100 cenários randômicos |

---

## 8. Arquivos

| Arquivo | Mudança |
|---------|---------|
| `src/strategy/indicators.py` | Modificado — adicionar `atr()` |
| `src/trading/risk_manager.py` | Modificado — `calculate()` com ATR + guard |
| `src/config/settings.py` | Modificado — novos campos `SIZING_MODE`, `RISK_PER_TRADE_USDT`, `ATR_*`, `MIN/MAX_POSITION_USDT`, `atr_multiplier_overrides` |
| `src/main.py` | Modificado — wiring de `get_atr_multiplier_override` no RiskManager |
| `tests/strategy/test_indicators.py` | Modificado — TEST_029_01, 02 |
| `tests/trading/test_risk_manager.py` | Modificado — TEST_029_03 a 08 |
| `tools/simulacao_atr_calibracao.py` | Novo — script de simulação (5 pares, 8 multipliers) |

---

## 9. Simulação para Calibração do `atr_multiplier`

**Responsável:** Quant Developer
**Prazo:** Antes da implementação

### Pares para simulação
- BTCUSDT — alta liquidez, ATR moderado (referência base)
- BROCCOLI714USDT — baixo preço, ATR pequeno (pior caso de descolamento fractal/ATR)
- XAUUSDT — commodity-like, ATR errático (teste de estresse)
- QNTUSDT — mid-cap, volatilidade média (representante do meio)
- SOLUSDT — alta volatilidade, boa liquidez (contraponto BTC)

### O que medir
- `atr_multiplier` variando de 1.0 a 5.0 (step 0.5)
- % de vezes que o guard atuou (fractal_sl_distance > atr * mult)
- % de vezes que o ATR dominou (atr * mult >= fractal_sl_distance)
- Distribuição do `effective_stop` vs. `fractal_sl_distance` por par
- Risco real médio e máximo vs. `RISK_PER_TRADE_USDT` configurado

### Homologação
- Trader Sênior precisa homologar o `atr_multiplier` final pós-simulação
- Se simulação mostrar que `multiplier > 3.0` para não superproteger, Time A reabre discussão

---

## 10. Definition of Done

- [x] `indicators.atr()` implementado e testado (TEST_029_01, 02)
- [x] `RiskManager.calculate()` com suporte ATR + `effective_stop` guard
- [x] Config `SIZING_MODE` alternando entre `fixed` e `atr`
- [x] Logging de `effective_stop`, `atr_value`, `fractal_sl_distance` em todo cálculo ATR
- [x] Fallback para fixed em caso de dados insuficientes
- [x] INV-029-01 a 06 implementados e testados
- [x] TEST_029_01 a 08 passando (712 total na suite)
- [x] Simulação 5 pares executada; `atr_multiplier=2.0` homologado
- [x] `ruff check src/ tests/` limpo

---

## 11. Histórico de Versões

| Versão | Data | Autor | Mudanças |
|--------|------|-------|----------|
| 1.0 | 2026-05-10 | Time B | Rascunho inicial |
| 2.0 | 2026-05-11 | Time A (Refinamento) | Refinamento completo: `atr_with_guard`, INV-029-05/06, simulação 5 pares, logging effective_stop, DoD expandido |
