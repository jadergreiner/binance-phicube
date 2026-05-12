# PLAN — Position Sizing por ATR

**Vinculado a:** SPEC_029 — Position Sizing por ATR
**PRD:** [`PRD.md`](./PRD.md)
**SPEC:** [`SPEC.md`](./SPEC.md)
**Data:** 2026-05-11
**Versão:** 1.0
**Responsável:** Time B (Execução)

---

## 0. Filosofia do Plano

Este plano não é uma lista de tarefas. É um **grafo de decisões** onde cada nó representa uma escolha que fecha alternativas e habilita a próxima. O plano reconhece que implementar ATR é trivial (20 linhas); o trabalho real está em **calibrar, validar e não quebrar o que já funciona**.

---

## 1. Mapa de Dependências

```
                /── 2.0 Simulação (offline) ──\         /── 4.0 Calibração Multiplier ──\
               /                               \       /                                 \
1.0 ATR() ────/                                 \─────/                                   \──── 5.0 Homologação
               \                               /       \                                 /        Trader
                \── 3.0 Settings ─────────────/         \── 4.1 Simetria Testes ────────/
                                              \
                                               \── 3.1 RiskManager ── 3.2 Guard ── 3.3 Clamp ── 3.4 Fallback
                                                                    \
                                                                     \── 3.5 Logging

6.0 Rollout ── 6.1 Monitoramento ── 6.2 Rollback
```

**Regra do grafo:** cada nó só pode ser iniciado quando todos os pais imediatos estão verdes.

---

## 2. Fases Detalhadas

---

### Fase 1 — `indicators.atr()` (Fundação)

**Esforço:** 2-4h
**Paralelizável:** Sim (independente do resto)

#### 1.1 Implementação

```python
# src/strategy/indicators.py

def atr(
    close: pd.Series,
    high: pd.Series,
    low: pd.Series,
    period: int = 14,
) -> pd.Series:
    """Average True Range — Wilder's smoothed ATR.

    Implementação: SMMA do True Range (média móvel suavizada de Wilder).
    Diferente de SMA porque o primeiro valor é SMA e os seguintes são
    atualizados recursivamente: atr[i] = (atr[i-1] * (period-1) + tr[i]) / period

    Isso dá peso exponencial decrescente ao histórico — reage mais rápido
    a mudanças de volatilidade que SMA puro.
    """
    tr = true_range(high, low, close)  # função auxiliar
    atr_series = pd.Series(index=close.index, dtype=float)

    # Primeiro valor: SMA do TR nos primeiros `period` candles
    atr_series.iloc[period - 1] = tr.iloc[1:period].mean()

    # Demais valores: SMMA recursivo de Wilder
    for i in range(period, len(tr)):
        atr_series.iloc[i] = (atr_series.iloc[i - 1] * (period - 1) + tr.iloc[i]) / period

    return atr_series
```

#### 1.2 True Range — função auxiliar

Criar `_true_range()` como função interna ou pública:

```python
def _true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """True Range: max(high - low, abs(high - prev_close), abs(low - prev_close))."""
    prev_close = close.shift(1)
    return pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
```

> ⚠️ **Não óbvio:** `prev_close` no índice 0 será NaN, o que faz `max(axis=1)` retornar NaN na primeira linha — comportamento correto (primeiro TR é sempre NaN). Testar explicitamente este edge case.

#### 1.3 Validação com série conhecida

Usar dados do Yahoo Finance ou planilha Phicube:

| Período | High | Low | Close | TR (calc) | ATR(14) esperado |
|---------|------|-----|-------|-----------|-----------------|
| 1 | 100 | 95 | 98 | 5 | NaN |
| ... | ... | ... | ... | ... | ... |
| 14 | ... | ... | ... | ... | 4.32 |
| 15 | ... | ... | ... | ... | 4.28 |

> **Decisão de implementação:** usar `pandas.Series` puro, sem numpy. Motivo: coerência com os indicadores existentes no arquivo que já usam pandas. ATR de Wilder é O(n) — eficiente o suficiente para DataFrames de até 1000 candles.

---

### Fase 2 — Simulação de Calibração (Paralela à Fase 1)

**Esforço:** 4-6h
**Paralelizável:** Sim (roda offline, não depende de código do bot)
**Responsável:** Quant Developer

#### 2.1 Script de simulação

Criar `tools/simulacao_atr_calibracao.py` — script standalone que:

1. **Baixa OHLCV** de 5 pares via ccxt (ou de arquivos CSV se preferir offline)
   - BTCUSDT, BROCCOLI714USDT, XAUUSDT, QNTUSDT, SOLUSDT
   - Timeframes: 15m (ou o timeframe principal de cada par)
   - Período: 30 dias corridos
2. **Para cada candle**, calcula:
   - `atr_value` (período 14, Wilder SMMA)
   - `fractal_sl_distance` simulado (estimativa: 1.5x a média do True Range)
   - `effective_stop = max(fractal_sl_distance, atr_value * multiplier)`
3. **Varre multiplier** de 1.0 a 5.0 (step 0.5)
4. **Métricas coletadas:**

| Métrica | Definição | Critério |
|---------|-----------|----------|
| `guard_activation_pct` | % candles onde fractal > ATR*mult | Mostra frequência que o guard protege |
| `atr_dominance_pct` | % candles onde ATR*mult >= fractal | Mostra frequência que ATR dita sizing |
| `risk_overshoot_p95` | Percentil 95 do risco real / risk_config | Mede o "estrago" do superdimensionamento |
| `position_reduction_pct` | % de redução vs. fixed sizing | Mede o "custo de oportunidade" |

#### 2.2 Saída esperada

```csv
symbol,multiplier,guard_activation_pct,atr_dominance_pct,risk_overshoot_p95,position_reduction_pct
BTCUSDT,1.0,12.3,87.7,1.02,34.2
BTCUSDT,1.5,8.1,91.9,1.01,28.7
...
BROCCOLI714,1.0,45.2,54.8,3.45,12.1
BROCCOLI714,1.5,31.8,68.2,2.10,8.9
...
```

#### 2.3 Decisão de calibração

> **Não óbvio:** O `atr_multiplier` não precisa ser global. Podemos ter um **default global** (1.5) e permitir **override por par** via `.env` (`ATR_MULTIPLIER_OVERRIDES={"XAUUSDT":3.0}`). A simulação vai mostrar que BROCCOLI714 precisa de multiplier maior para não superproteger — override por par resolve sem penalizar BTC.

#### 2.4 Artefato da simulação

Salvar resultados em `docs/SDD/SPEC_029_POSITION_SIZING_ATR/calibracao_atr_multiplier.csv` e um **gráfico** `calibracao_atr_multiplier.png` com:
- Eixo X: multiplier
- Eixo Y: risk_overshoot_p95 (linha vermelha: tolerância 1.05)
- Uma curva por par
- Linha vertical no multiplier escolhido

---

### Fase 3 — Integração no RiskManager

**Esforço:** 6-8h
**Paralelizável:** Depende de Fase 1 (ATR pronta)

#### 3.1 Settings — novos campos

```python
# src/config/settings.py

class SizingMode(str, Enum):
    FIXED = "fixed"
    ATR = "atr"

class Settings(BaseSettings):
    # ... campos existentes ...

    # SPEC_029 — Position Sizing por ATR
    sizing_mode: SizingMode = SizingMode.FIXED
    risk_per_trade_usdt: float = 5.0
    atr_period: int = 14
    atr_multiplier: float = 1.5
    min_position_usdt: float = 10.0
    max_position_usdt: float = 500.0
```

> ⚠️ **Não óbvio:** `risk_per_trade_usdt` e `risk_per_trade_pct` **coexistem**. Quando `SIZING_MODE=atr`, o campo `risk_per_trade_pct` não é usado para sizing, mas continua sendo lido para outros cálculos (ex: relatório de performance mostra % do saldo arriscado). Não remover — apenas ignorar condicionalmente.

#### 3.2 RiskManager — método `calculate_position_size()`

Assinatura implementada:

```python
def calculate(
    self,
    signal: Signal,
    available_balance: float,
    quantity_precision: int = 3,
    intraday_realized_pnl_usdt: float = 0.0,
    now_utc: datetime | None = None,
    df: pd.DataFrame | None = None,
) -> PositionSize | None:
```

O `df` é opcional porque o TradingMonitor já tem o DataFrame na memória quando chama o RiskManager. Mas em outros contextos (testes, backtest) pode não estar disponível. A assinatura aceita `None` e faz fallback para fixed — sem quebrar.

#### 3.3 Guard Implementation (código real)

A implementação real usa injeção de dependência via construtor (não `self._settings`), `_compute_atr_value()` como Facade, e retorna `None` com `_set_rejection()` em vez de `raise`. Ver `risk_manager.py:216-241` para o fluxo completo.

```python
# Dentro de calculate() — ver risk_manager.py:216-241
if self._sizing_mode == SizingMode.ATR and df is not None:
    result = self._calculate_atr(
        signal=signal,
        stop_distance=stop_distance,
        quantity_precision=quantity_precision,
        df=df,
        available_balance=available_balance,
    )
    if result is not None:
        return result
    # Fallback silencioso
    logger.info("atr_fallback_to_fixed", symbol=signal.symbol)

return self._calculate_fixed(
    symbol=signal.symbol,
    direction=signal.direction,
    ...
)
```

O método `_calculate_atr()` (detalhes em `risk_manager.py:269-392`):
1. Calcula ATR via `_compute_atr_value(df)` (Facade)
2. Se atr_value <= 0 → retorna None (fallback)
3. `effective_stop = max(fractal_sl_distance, atr_value * multiplier)`
4. `position_usdt = effective_risk_per_trade_usdt * entry_price / effective_stop`
5. Aplica `max_position_pct` se configurado
6. Aplica clamp em [min_position_usdt, max_position_usdt]
7. Valida INV-029-05: `actual_risk_usdt > max_risk_usdt * 1.05` → `_set_rejection()` → None
8. Valida slippage gate (SPEC_043): `_check_slippage_gate()` → None se exceder
9. Log: `atr_sizing_calculated`
10. Retorna `PositionSize`

#### 3.4 Método `_calculate_fixed()` extraído

> **Não óbvio:** Extrair a lógica atual de `calculate_position_size()` para `_calculate_fixed()` evita duplicação e mantém o modo legado isolado. Se no futuro removermos o modo fixed, o código morto fica explícito.

```python
def _calculate_fixed(
    self,
    symbol: str,
    direction: Direction,
    entry_price: float,
    stop_price: float,
    take_profit: float,
    available_balance: float,
    quantity_precision: int = 3,
) -> PositionSize | None:
    """Comportamento legado: risk_per_trade_pct do saldo."""
    # ... lógica existente (ver risk_manager.py:394-488) ...
```

#### 3.5 Logging — estrutura do log

```python
logger.info(
    "atr_sizing_calculated",
    symbol=symbol,
    direction=direction,
    atr_value=round(atr_value, 4),
    fractal_sl_distance=round(fractal_sl_distance, 2),
    effective_stop=round(effective_stop, 2),
    position_usdt=round(position_usdt, 2),
    risk_per_trade_usdt=self._settings.risk_per_trade_usdt,
    sizing_mode="atr",
)
```

> **Não óbvio:** O campo `effective_stop` é a chave para auditoria pós-rollout. Permite verificar em produção qual dos dois mecanismos (fractal ou ATR) está ditando o sizing. Um dashboard futuro pode plotar `effective_stop / fractal_sl_distance` ao longo do tempo para identificar padrões de superproteção.

---

### Fase 4 — Testes (Paralelo à Fase 3)

**Esforço:** 4-6h
**Paralelizável:** Sim (testes do ATR são independentes dos testes de integração)

#### 4.1 TEST_029_01 — ATR com série conhecida

```python
def test_atr_calcula_corretamente_serie_conhecida():
    """Usar dados manuais onde ATR(14) é conhecido."""
    close = pd.Series([...])
    high = pd.Series([...])
    low = pd.Series([...])
    result = atr(close, high, low, period=14)
    assert round(result.iloc[13], 4) == 4.32  # valor calculado manualmente
    assert result.iloc[12] != result.iloc[13]  # primeiro valor não-NaN
```

#### 4.2 TEST_029_02 — NaN inicial

```python
def test_atr_retorna_nan_nos_primeiros_period_candles():
    close = pd.Series(range(100))
    high = pd.Series(range(100))
    low = pd.Series(range(100))
    result = atr(close, high, low, period=14)
    assert result.isna().sum() == 14
    assert not result.iloc[14:].isna().any()  # após period-1, todos válidos
```

#### 4.3 TEST_029_03 a 05 — Guard ATR

```python
@pytest.mark.parametrize("fractal_dist,atr_val,mult,expected_stop", [
    # Guard atua (fractal > ATR * mult)
    (100, 20, 3, 100),    # fractal=100, ATR*3=60 → stop=100
    (50, 20, 3, 60),      # fractal=50, ATR*3=60 → stop=60
    # Equal
    (60, 20, 3, 60),      # fractal=60, ATR*3=60 → stop=60
    # Edge: fractal = 0 (caso raro, SL colado)
    (0, 20, 3, 60),       # fractal=0, ATR*3=60 → stop=60
])
async def test_atr_guard_effective_stop(
    fractal_dist, atr_val, mult, expected_stop,
    risk_manager, mocker
):
    """Testa que effective_stop = max(fractal_sl_distance, atr * mult)."""
    mock_atr = mocker.patch("src.strategy.indicators.atr")
    mock_atr.return_value = pd.Series([atr_val] * 20)
    # ...
```

#### 4.4 TEST_029_06 — Clamp

```python
@pytest.mark.parametrize("raw_pos,min_pos,max_pos,expected", [
    (5, 10, 500, 10),    # abaixo do mínimo → sobe para min
    (600, 10, 500, 500), # acima do máximo → desce para max
    (100, 10, 500, 100), # dentro do range → mantém
    (10, 10, 500, 10),   # exatamente no mínimo
    (500, 10, 500, 500), # exatamente no máximo
])
async def test_atr_sizing_clamp(raw_pos, min_pos, max_pos, expected, ...):
    ...
```

#### 4.5 TEST_029_07 — Fallback

```python
async def test_atr_fallback_para_quando_df_vazio():
    """Se SIZING_MODE=atr mas df=None, cai para fixed sem erro."""
    ...
```

#### 4.6 TEST_029_08 — INV-029-05 (100 cenários randômicos)

```python
@pytest.mark.parametrize("seed", range(100))
async def test_inv_029_05_risco_real_nunca_excede_tolerancia(seed):
    """100 cenários com parâmetros aleatórios validam invariante."""
    rng = random.Random(seed)
    entry = rng.uniform(1, 50000)
    stop = entry * (1 - rng.uniform(0.005, 0.05))
    atr_val = rng.uniform(entry * 0.001, entry * 0.02)
    mult = rng.uniform(1.0, 5.0)
    risk_usdt = rng.uniform(1, 50)
    min_pos = rng.uniform(5, 50)
    max_pos = rng.uniform(100, 2000)

    # Cálculo
    sl_dist = abs(entry - stop)
    eff_stop = max(sl_dist, atr_val * mult)
    pos_usdt = risk_usdt * entry / eff_stop
    pos_usdt = max(min_pos, min(pos_usdt, max_pos))
    actual_risk = pos_usdt * eff_stop / entry

    assert actual_risk <= risk_usdt * 1.05, (
        f"seed={seed}: actual_risk={actual_risk:.2f} > {risk_usdt * 1.05:.2f}"
    )
```

> **Não óbvio:** TEST_029_08 é o teste mais importante. Ele varre o espaço de parâmetros com sementes aleatórias — cobre combinações que nenhum teste manual pensaria. É o "fuzzing" da invariante. Rodar com `pytest -n auto` para paralelizar os 100 cenários.

---

### Fase 5 — Homologação

**Esforço:** 2-4h
**Paralelizável:** Não (depende de todas as fases anteriores)

#### 5.1 Revisão do Trader Sênior

Checklist:

- [ ] Simulação executada com 5 pares
- [ ] `atr_multiplier` definido com base nos dados
- [ ] Override por par documentado (se aplicável)
- [ ] `RISK_PER_TRADE_USDT` default validado contra saldo atual ($300)
- [ ] Logging de `effective_stop` inspecionado

#### 5.2 Gate de aprovação

```yaml
# .github/workflows/gates/spec029-gate.yml
name: SPEC_029 Homologation Gate
on: [workflow_dispatch]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -e ".[dev]"
      - run: pytest tests/strategy/test_indicators.py::test_atr* -v
      - run: pytest tests/trading/test_risk_manager.py::test_atr* -v
      - run: pytest tests/trading/test_risk_manager.py::test_inv_029_05 -v
      - run: ruff check src/trading/risk_manager.py src/strategy/indicators.py
```

---

### Fase 6 — Rollout

**Esforço:** 2-4h
**Paralelizável:** Monitoramento contínuo após deploy

#### 6.1 Estratégia de rollout

| Passo | Ação | Verificação | Rollback |
|-------|------|-------------|----------|
| 1 | Deploy com `SIZING_MODE=fixed` (default) | Bot sobe, trades continuam como antes | `git revert` |
| 2 | Operador ativa `SIZING_MODE=atr` manualmente | Logs mostram `atr_sizing_calculated` | Voltar para `fixed` |
| 3 | Monitorar 24h | Nenhum INV-029-05 violado | Ajustar multiplier |
| 4 | Se tudo ok, tornar `atr` default futuro | ... | ... |

#### 6.2 Monitoramento pós-rollout

**O que observar nas primeiras 24h:**

1. **Logs de `atr_sizing_calculated`** — todo trade ATR deve ter esta linha
2. **`effective_stop` médio por par** — comparar com `fractal_sl_distance` médio
3. **Quantidade de fallbacks** — logs `atr_value_is_nan_fallback_to_fixed` devem ser raros
4. **Trades rejeitados** — `REJECTED_RISK_QTY_ZERO` deve cair a zero nos pares que antes não abriam

**Comando de diagnóstico:**

```bash
# Extrair métricas ATR dos logs recentes
python tools/phicube_ops_cli.py doctor --json | jq '.sizing_atr'
```

> **Não óbvio:** Se após rollout o `effective_stop` estiver atuando em >50% dos trades de um par específico, o `atr_multiplier` está muito baixo para aquele par. O override por par (`ATR_MULTIPLIER_{SYMBOL}`) deve ser ativado. Criar alerta no logger se `guard_activation_pct > 50%` para qualquer símbolo nas primeiras 24h.

#### 6.3 Plano de rollback

```bash
# Imediato: voltar para fixed sem redeploy
docker exec phicube env SIZING_MODE=fixed
# OU
# Alterar .env e recriar container
sed -i 's/SIZING_MODE=atr/SIZING_MODE=fixed/' .env
docker compose up -d phicube
```

> ⚠️ Rollback via env var não requer build — apenas restart. O RiskManager lê o settings em cada execução (`get_settings()` cacheado), então trocar a env var e restartar o container é instantâneo e seguro.

---

## 3. Riscos Não-óbvios do Plano

| Risco | Probabilidade | Impacto | Detecção | Mitigação |
|-------|--------------|---------|----------|-----------|
| **Simulação offline vs. produção divergem** | Média | Alto — multiplier calibrado errado | Discrepância >10% nas métricas de guard activation | Usar dados REAIS dos 29 símbolos (fetch_ohlcv_with_retry), não mock |
| **ATR em timeframe 1h para par que opera em 15m** | Baixa | Alto — volatilidade 4x diferente | `effective_stop` consistentemente maior que `fractal_sl_distance` | Validação estática: comparar ATR do df passado vs. timeframe do par |
| **Múltiplos trades simultâneos no mesmo par com ATR** | Baixa | Baixo — posições somadas podem exceder max sem violar INV-029-05 | Log agregado por símbolo | Já protegido por `MAX_OPEN_POSITIONS` e `MAX_CAPITAL_ALLOCATION_PCT` |
| **Rounding de quantity zera posição ATR** | Baixa | Médio — trade não abre apesar de ATR ter calculado posição > min | Log `quantity_zero_after_rounding` | Já capturado pelo RiskManager existente; ATR apenas muda o position_usdt, o rounding é o mesmo |
| **ATR em dado corrompido (OHLCV com zeros)** | Muito Baixa | Alto — ATR = 0, effective_stop = 0, divisão por zero | `atr_value = 0` → `effective_stop = 0` → crash | Proteção: se `atr_value <= 0`, fallback para fixed |
| **Backtest vs. produção: ATR em dados históricos vs. streaming** | Média | Médio — backtest pode ficar otimista se não usar o mesmo ATR | Comparar sinal gerado em backtest vs. produção para mesmo período | Usar `shift(1)` no ATR para evitar look-ahead bias |

> **Edge case extremo:** Se o par está em **gap (abertura muito longe do fechamento anterior)**, o True Range dispara → ATR sobe → `effective_stop` é dominado pelo ATR → posição reduz. Isso é **comportamento correto**: gap = aumento de volatilidade = redução de posição. Mas o operador pode estranhar se o trade não abrir. Documentar este comportamento no `docs/OPERATIONS.md`.

---

## 4. Matriz de Responsabilidades

| Papel | Fase 1 | Fase 2 | Fase 3 | Fase 4 | Fase 5 | Fase 6 |
|-------|--------|--------|--------|--------|--------|--------|
| Backend Sênior | Implementa ATR() | — | Settings + RiskManager | Testes unitários | — | Rollout |
| Quant Developer | Validação matemática | Script simulação | — | TEST_029_08 (fuzzing) | Análise simulação | Monitoramento |
| QA Engineer | — | — | — | Testes integração | Gate validação | Testes pós-rollout |
| Trader Sênior | — | — | — | — | Homologa multiplier | Aprova rollout |
| Devops | — | — | — | — | CI gate | Rollback script |

---

## 5. Timeline Estimada

```
Semana 1:
  Seg:  [Fase 1] ATR() implementação + teste manual
        [Fase 2] Script simulação + início coleta dados
  Ter:  [Fase 1] TEST_029_01, 02
        [Fase 2] Resultados simulação + gráfico
  Qua:  [Fase 3] Settings + RiskManager + Guard + Clamp
        [Fase 4] TEST_029_03 a 07
  Qui:  [Fase 4] TEST_029_08 (fuzzing) + integração
        [Fase 5] Revisão Trader Sênior
  Sex:  [Fase 5] Homologação
        [Fase 6] Rollout + monitoramento 24h

Total: ~5 dias (com margem para imprevistos)
```

---

## 6. Entregáveis

| ID | Entregável | Dono | Prazo |
|----|-----------|------|-------|
| E1 | `src/strategy/indicators.py` — função `atr()` | Backend | Seg |
| E2 | `tools/simulacao_atr_calibracao.py` | Quant | Ter |
| E3 | `docs/SDD/SPEC_029_POSITION_SIZING_ATR/calibracao_atr_multiplier.csv` | Quant | Ter |
| E4 | `src/config/settings.py` — novos campos | Backend | Qua |
| E5 | `src/trading/risk_manager.py` — método modificado | Backend | Qua |
| E6 | `tests/strategy/test_indicators.py` — TEST_029_01, 02 | Backend+QA | Qua |
| E7 | `tests/trading/test_risk_manager.py` — TEST_029_03 a 08 | QA+Quant | Qui |
| E8 | Homologação assinada pelo Trader Sênior | Trader | Sex |
| E9 | Rollout em produção + 24h de monitoramento | Backend+Devops | Sex |

---

## 7. Plano de Contingência

| Cenário | Gatilho | Ação |
|---------|---------|------|
| Simulação mostra `risk_overshoot_p95 > 1.10` para qualquer multiplier | Resultado simulação | Time A reabre discussão — `atr_with_guard` pode precisar de fórmula alternativa |
| Fallback ATR > 5% dos trades na primeira semana | Log monitoring | Investigar: OHLCV corrompido? Timeframe errado? Period grande demais? |
| Trader Sênior rejeita multiplier > 3.0 | Gate homologação | Reabrir Time A para definir regra de override por par |
| INV-029-05 violado em produção | Log ERROR | Rollback imediato para `SIZING_MODE=fixed` + análise de causa |
| ATR em produção difere >20% do ATR da simulação | Comparação logs vs. simulação | Recalibrar com dados reais de produção, não históricos |

---

## 8. Métricas de Sucesso Pós-Rollout

| Métrica | Janela | Alvo | Como Medir |
|---------|--------|------|------------|
| Trades rejeitados por `quantity_zero_after_rounding` | 7 dias pós-rollout | 0 (zero) | Dashboard + MongoDB |
| Fallbacks para fixed (`atr_value_is_nan`) | 7 dias pós-rollout | <1% dos trades | Logs |
| `effective_stop` mediano = `fractal_sl_distance` | 7 dias pós-rollout | ≥ 60% dos trades (fractal dita sizing, não ATR) | Logs |
| INV-029-05 violações | 30 dias pós-rollout | 0 | Log ERROR |
| Risco real mediano / `RISK_PER_TRADE_USDT` | 30 dias | ≤ 1.05 | Logs agregados |

---

*Este plano é um documento vivo — atualizar conforme descobertas durante a execução.*
