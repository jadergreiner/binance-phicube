# SPEC_029 — Position Sizing por ATR

**ID:** SPEC_029
**Título:** Position Sizing por ATR
**Data:** 2026-05-10
**Status:** Rascunho
**Versão:** 1.0
**Dependências:** SPEC_006 (métricas), SPEC_022 (convergência risco)
**PRD §:** Fase 2 — "Gestão de risco dinâmica"

---

## 1. Objetivo

Substituir o position sizing fixo (`POSITION_SIZE_USDT`) por um modelo dinâmico baseado em ATR (Average True Range) que ajusta o tamanho da posição conforme a volatilidade do par. Posições maiores em ativos de baixa volatilidade, menores em ativos voláteis — mantendo risco constante em USDT.

---

## 2. Escopo

### Dentro do escopo
- Cálculo de ATR no `indicators.py` (média do True Range nos últimos N candles)
- Novo modelo de sizing: `risk_usdt / (atr * atr_multiplier)`
- Risco fixo em USDT configurável (`RISK_PER_TRADE_USDT`)
- Fallback para sizing fixo se ATR indisponível (poucos candles)
- Integração com `RiskManager.calculate_position_size()`
- Flag de ativação: `SIZING_MODE = "fixed" | "atr"`

### Fora do escopo
- Sizing baseado em Kelly Criterion
- Sizing por saldo total da conta (fração de equity)
- Redução progressiva de posição em drawdown

---

## 3. User Stories

### US-029-01 — Cálculo de ATR no indicators
**Como** engenheiro,
**quero** ter `indicators.atr(close, high, low, period=14)` disponível,
**para** usar no sizing e futuramente em stops dinâmicos.

**Critério de aceite:**
- Retorna `pd.Series` mesmo comprimento que entrada
- NaN nos primeiros `period` candles

### US-029-02 — Sizing por ATR no RiskManager
**Como** operador,
**quero** configurar `SIZING_MODE=atr` e `RISK_PER_TRADE_USDT=50`,
**para** que cada trade arrisque exatos 50 USDT independente do par.

**Critério de aceite:**
- `SIZING_MODE=fixed` → comportamento atual (`POSITION_SIZE_USDT`)
- `SIZING_MODE=atr` → posição = `risk_usdt / (atr * multiplier)`
- Posição mínima respeitada: não menor que min notional da Binance

---

## 4. Modelo de Dados

### RiskManager — novo campo de configuração

| Campo | Tipo | Default | Descrição |
|-------|------|---------|-----------|
| `sizing_mode` | `SizingMode` | `"fixed"` | `"fixed"` ou `"atr"` |
| `risk_per_trade_usdt` | `float` | `50.0` | Risco máximo por trade (USDT) |
| `atr_period` | `int` | `14` | Período do ATR |
| `atr_multiplier` | `float` | `1.5` | Distância SL em ATR |
| `min_position_usdt` | `float` | `10.0` | Posição mínima (min notional) |
| `max_position_usdt` | `float` | `1000.0` | Posição máxima (cap de segurança) |

### Fórmula de sizing (ATR mode)

```
atr = indicators.atr(close, high, low, period=14).iloc[-1]
sl_distance = atr * atr_multiplier        # distância do SL em USDT (preço)
position_size = risk_per_trade_usdt / (sl_distance / entry_price)
position_size = clamp(position_size, min_position_usdt, max_position_usdt)
```

---

## 5. Componentes

### 5.1 `src/strategy/indicators.py` — nova função

```python
def atr(close: pd.Series, high: pd.Series, low: pd.Series, period: int = 14) -> pd.Series:
    """Average True Range — Wilder's smoothed ATR."""
```

### 5.2 `src/trading/risk_manager.py` — método modificado

```python
class RiskManager:
    async def calculate_position_size(
        self, symbol: str, direction: str, df: pd.DataFrame
    ) -> float:
        """Retorna tamanho da posição em USDT."""
```

**Algoritmo ATR:**
1. Se `sizing_mode == "fixed"`: retorna `POSITION_SIZE_USDT`
2. Se `sizing_mode == "atr"`:
   - Calcula ATR no DataFrame
   - Se último ATR for NaN → fallback para fixed
   - `sl_distance_usdt = atr_value * atr_multiplier`
   - `position = risk_per_trade_usdt / (sl_distance_usdt / current_price)`
   - Aplica `clamp` (min/max position)
   - Converte para quantidade do ativo: `position / current_price`

---

## 6. Invariantes

| ID | Invariante |
|----|-----------|
| INV-029-01 | `position_size` nunca excede `max_position_usdt` |
| INV-029-02 | `position_size` nunca é menor que `min_position_usdt` |
| INV-029-03 | Se ATR for NaN no último candle, sizing cai para fixed |
| INV-029-04 | `risk_per_trade_usdt` > 0 sempre |

---

## 7. Testes

| ID | Descrição |
|----|-----------|
| TEST_029_01 | ATR calculado corretamente para série conhecida |
| TEST_029_02 | ATR retorna NaN nos primeiros `period` candles |
| TEST_029_03 | Sizing ATR: posição maior em baixa volatilidade, menor em alta |
| TEST_029_04 | Fallback para fixed quando ATR indisponível |
| TEST_029_05 | Clamp respeita min/max_position_usdt |
| TEST_029_06 | Sizing mode = fixed mantém comportamento atual |

---

## 8. Arquivos

| Arquivo | Mudança |
|---------|---------|
| `src/strategy/indicators.py` | Modificado — adicionar `atr()` |
| `src/trading/risk_manager.py` | Modificado — `calculate_position_size()` com ATR |
| `src/config/settings.py` | Modificado — novos campos `SIZING_MODE`, `RISK_PER_TRADE`, `ATR_*` |
| `tests/strategy/test_indicators.py` | Modificado — TEST_029_01, 02 |
| `tests/trading/test_risk_manager.py` | Modificado — TEST_029_03 a 06 |

---

## 9. Definition of Done

- [ ] `indicators.atr()` implementado e testado com série conhecida
- [ ] `RiskManager.calculate_position_size()` com suporte ATR
- [ ] Config `SIZING_MODE` alternando entre fixed e atr
- [ ] Fallback para fixed em caso de dados insuficientes
- [ ] Min/max position respeitados
- [ ] TEST_029_01 a 06 passando
- [ ] `ruff check src/ tests/` limpo
