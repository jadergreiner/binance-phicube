# SPEC_028 — Realismo em Backtest: Slippage, Taxas e Sizing

**ID:** SPEC_028
**Título:** Realismo em Backtest: Slippage, Taxas e Sizing
**Data:** 2026-05-10
**Status:** Concluída
**Versão:** 2.0
**Dependências:** SPEC_011 (Motor de Backtesting)
**PRD §:** Fase 2 — "Backtests e walk-forward analysis"

---

## 1. Objetivo

Adicionar slippage por tier de liquidez, taxas Binance (maker/taker) e **sizing real via RiskManager** ao `BacktestEngine` para que os resultados de backtest reflitam condições reais de mercado, eliminando o viés otimista do modelo atual.

O motor hoje:
- Assume entrada/saída no close exato do candle — sem slippage
- Ignora taxas de corretagem
- Usa fórmula linear `pnl = Δpreço * saldo / entry`, ignorando o RiskManager real (erro de ~2x no PnL)

---

## 2. Escopo

### Dentro do escopo (MVP)
- Slippage percentual por **tier de liquidez** (3 níveis: high/medium/low) com lookup map por símbolo
- Taxas Binance: 0.02% maker / 0.05% taker (padrão VIP 0), configuráveis
- Slippage aplicado na entrada (market) e saída (SL/TP hit via stop order)
- **RiskManager integrado ao cálculo de PnL** quando `--realistic` ativo
- Flag `--realistic` no CLI e `realistic=true` na API
- Resultado exibido com **Gross e Net** lado a lado para comparação
- **Alerta informacional composto** (IC win rate, razão net/gross, N pequeno, múltiplas runs)
- **Logging de parâmetros** sempre ativo em `backtest_runs.jsonl` (append-only)
- Slippage override explícito via `--override-slippage <pct>` (gera WARN no log)

### Fora do escopo (MVP)
- Slippage flat (USDT por ordem) — **removido**: quebra para pares abaixo de ~100 USDT
- Slippage estocástico — **rejeitado**: impacto <0,3% do PnL total; ROI negativo para MVP
- Slippage por profundidade de livro de ofertas (order book)
- Slippage por volatilidade intrabar
- Taxas diferenciadas por nível VIP por conta
- Saldo virtual (equity variável) — postergado para SPEC_029
- Spread observado em tempo real — postergado (requer coleta histórica)

---

## 3. User Stories

### US-028-01 — Execução realista no CLI
**Como** operador,
**quero** executar `python -m src.backtest.runner --symbol BTCUSDT --timeframe 4h --realistic`,
**para** ver métricas com slippage, taxas e sizing real incluídos.

**Critério de aceite:**
- Saída exibe colunas extras: `total_fees`, `total_slippage`
- Resultado realista tem PnL menor ou igual ao sem custos
- Alerta informacional exibido quando aplicável (N < 50, net/gross < 0.5, etc.)

### US-028-02 — Comparação lado a lado
**Como** operador,
**quero** ver `BacktestResult` com campos `gross` e `net` na mesma execução,
**para** entender o impacto realista da estratégia.

**Critério de aceite:**
- `BacktestResult` inclui `gross` e `net` (ambos `BacktestResult`)
- Quando `realistic=false`: `gross == net` (mesmo resultado, sem custos)
- Quando `realistic=true`: `gross ≠ net`, diferença reflete custos + sizing real

### US-028-03 — Sizing realista via RiskManager (NOVO)
**Como** operador,
**quero** que o PnL do backtest use o mesmo `RiskManager` do trading ao vivo,
**para** que o resultado reflita o tamanho de posição real e não uma aproximação linear.

**Critério de aceite:**
- `--realistic` ativa `RiskManager.calculate()` para dimensionar posição
- Sem `--realistic`, engine preserva comportamento original (compatibilidade reversa)
- PnL realista = `(exit_price - entry) * position.quantity` (vs. fórmula linear antiga)

### US-028-04 — Alerta informacional (NOVO)
**Como** operador,
**quero** receber alertas contextuais sobre a confiabilidade do resultado,
**para** tomar decisões informadas sem ser bloqueado.

**Critério de aceite:**
- CLI exibe seção `⚠️ Análise de Confiabilidade` com IC win rate, razão net/gross, alerta de múltiplas runs
- API retorna campo `warnings: list[str]`
- Nenhuma condição bloqueia execução (exit code 0 sempre)

### US-028-05 — Histórico de execuções (NOVO)
**Como** operador,
**quero** que cada backtest seja registrado automaticamente,
**para** que no futuro eu possa auditar quantas vezes ajustei parâmetros no mesmo par.

**Critério de aceite:**
- Cada execução append em `backtest_runs.jsonl`
- Logging ativo independentemente de `--realistic`

---

## 4. Modelo de Dados

### Extensões em `BacktestTrade`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `entry_fee` | `float` | Taxa paga na entrada (USDT) |
| `exit_fee` | `float` | Taxa paga na saída (USDT) |
| `slippage_entry_pct` | `float` | % de slippage aplicado na entrada |
| `slippage_exit_pct` | `float` | % de slippage aplicado na saída |
| `slippage_entry_usdt` | `float` | Deslize em USDT na entrada |
| `slippage_exit_usdt` | `float` | Deslize em USDT na saída |
| `pnl_gross_usdt` | `float` | PnL sem custos |
| `pnl_net_usdt` | `float` | PnL líquido (deduzindo taxas + slippage) |

> `pnl_usdt` existente permanece como alias para `pnl_gross_usdt` (compatibilidade reversa).

### Extensões em `BacktestResult`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `gross` | `BacktestResult` | Resultado sem custos (compatível com SPEC_011) |
| `net` | `BacktestResult` | Resultado com custos |
| `total_fees_usdt` | `float` | Soma total de taxas |
| `total_slippage_usdt` | `float` | Soma total de slippage |
| `warnings` | `list[str]` | Alertas informacionais (vazio se nenhum) |

> **Sempre presente:** `gross` e `net` são sempre serializados. Quando `realistic=false`, `gross == net`.

---

## 5. Componentes

### 5.1 Configuração (`src/config/settings.py` — extensão)

```python
# NOVO: Slippage percentual por tier de liquidez (substitui flat + pct genérico)
BACKTEST_SLIPPAGE_BY_LIQ: dict[str, float] = {
    "high": 0.0003,    # 0.03% — BTC, ETH
    "medium": 0.0008,  # 0.08% — SOL, LINK, AVAX
    "low": 0.0015,     # 0.15% — ADA, ALGO, XRP
}

BACKTEST_SLIPPAGE_LIQ_MAP: dict[str, str] = {
    # high liquidity
    "BTCUSDT": "high", "ETHUSDT": "high",
    # medium liquidity (default para não-listados)
    "SOLUSDT": "medium", "LINKUSDT": "medium",
    "AVAXUSDT": "medium", "DOTUSDT": "medium",
    "MATICUSDT": "medium", "ATOMUSDT": "medium",
    "UNIUSDT": "medium", "LTCUSDT": "medium",
    "BCHUSDT": "medium", "ETCUSDT": "medium",
    "FILUSDT": "medium", "NEARUSDT": "medium",
    "APTUSDT": "medium", "ARBUSDT": "medium",
    "OPUSDT": "medium", "INJUSDT": "medium",
    "RUNEUSDT": "medium", "AAVEUSDT": "medium",
    "MKRUSDT": "medium",
    # low liquidity
    "ADAUSDT": "low", "ALGOUSDT": "low",
    "XRPUSDT": "low", "DOGEUSDT": "low",
    "TRXUSDT": "low", "VETUSDT": "low",
    "ICPUSDT": "low", "XLMUSDT": "low",
    "HBARUSDT": "low", "EGLDUSDT": "low",
    "SANDUSDT": "low", "MANAUSDT": "low",
    "THETAUSDT": "low", "FTMUSDT": "low",
}
# Default para símbolos não listados no map: "medium"

# NOVO: Taxas Binance (padrão VIP 0)
BACKTEST_MAKER_FEE: float = 0.0002    # 0.02%
BACKTEST_TAKER_FEE: float = 0.0005    # 0.05%

# REMOVIDO (v1.0):
# BACKTEST_SLIPPAGE_FLAT: float = 0.5
# BACKTEST_SLIPPAGE_PCT: float = 0.0
```

### 5.2 BacktestEngine — novo método `_apply_costs`

```python
def _apply_costs(
    self,
    price: float,
    direction: Literal["LONG", "SHORT"],
    symbol: str,
    order_type: Literal["market", "stop"],
) -> tuple[float, float, float]:
    """Aplica slippage percentual por tier e taxa no preço dado.

    Args:
        price: Preço de referência (close do candle ou SL/TP).
        direction: Direção do trade.
        symbol: Símbolo para lookup do tier de liquidez.
        order_type: 'market' (entrada/saída) ou 'stop' (SL/TP).

    Returns:
        (price_with_slippage, fee_amount, slippage_amount_usdt)
    """
    liq_tier = self._settings.backtest_slippage_liq_map.get(symbol, "medium")
    slippage_pct = self._settings.backtest_slippage_by_liq[liq_tier]

    fee_pct = (
        self._settings.backtest_maker_fee
        if order_type == "stop"
        else self._settings.backtest_taker_fee
    )

    if direction == "LONG":
        adjusted_price = price * (1 + slippage_pct)
    else:
        adjusted_price = price * (1 - slippage_pct)

    fee = adjusted_price * fee_pct
    slippage_amount = abs(adjusted_price - price)
    return adjusted_price, fee, slippage_amount
```

### 5.3 RiskManager Integration (sizing real)

**Injeção:** `BacktestEngine.__init__` recebe `RiskManager` opcionalmente.

```python
class BacktestEngine:
    def __init__(self, settings: Settings, client: BinanceClient,
                 risk_manager: RiskManager | None = None) -> None:
        self._settings = settings
        self._client = client
        self._signal_engine = SignalEngine(risk_reward_ratio=settings.risk_reward_ratio)
        self._risk_manager = risk_manager  # None se não-realistic
```

**Uso no loop `run()`:**

```python
# No branch que fecha o trade:
if self._risk_manager is not None:  # modo realistic
    position = self._risk_manager.calculate(
        signal=signal,
        balance=self._initial_balance,
        position_type=PositionType.ENTRY,
        current_positions=[],
    )
    pnl = (exit_price - entry) * position.quantity
else:  # modo legado (compatibilidade reversa)
    pnl = (exit_price - entry) * self._initial_balance / entry
```

**Invariante de compatibilidade:**
- Se `risk_manager` é `None`, todo o pipeline de custos (slippage, taxas) é ignorado
- `BacktestResult.gross == BacktestResult.net` neste caso

### 5.4 Alerta Informacional Composto

Aplicado no output CLI e na resposta API quando `realistic=True`.

**Quatro condições monitoradas:**

| Condição | Gatilho | Mensagem |
|----------|---------|----------|
| Baixa significância | `N < 50` | "IC 95% win rate: [X%, Y%] — N={N} < 50, baixa significância estatística" |
| Degradação alta | `net_pnl / gross_pnl < 0.5` | "Degradação alta: custos consomem >50% do lucro bruto (razão net/gross={ratio})" |
| Crítico | Ambas acima | Alerta vermelho combinado |
| Múltiplas execuções | >3 runs no mesmo par em 24h | "Múltiplas execuções detectadas ({N} nas últimas 24h) — risco de data dredging" |

**Comportamento:**
- Nenhuma condição bloqueia execução — `exit code 0` sempre
- API retorna `BacktestResult.warnings: list[str]`
- CLI exibe seção `⚠️ Análise de Confiabilidade:` ao final do output

**Exemplo de saída CLI:**

```
=== Backtest Realista: BTCUSDT 4h ===
Trades: 35 | Gross PnL: +$245.30 | Net PnL: +$187.40
Taxas: $42.10 | Slippage: $15.80 | Degradação: 23.6%

⚠️  Análise de Confiabilidade:
   • IC 95% win rate: [44.2%, 76.8%] (N=35 < 50 — baixa significância)
   • Razão net/gross: 0.76 (saudável — > 0.5)
   • Degradação aceitável: custos consumiram 23.6% do lucro bruto
   • Esta é a execução #4 com parâmetros diferentes neste par (24h)
   → Considere walk-forward validation antes de decisão de produção.
```

### 5.5 Logging de Parâmetros (sempre ativo)

**Arquivo:** `backtest_runs.jsonl` (append-only, nunca sobrescreve)

**Formato (JSON Lines):**

```jsonl
{"ts":"2026-05-10T14:00:00Z","symbol":"BTCUSDT","tf":"4h",
 "params":{"realistic":true,"slippage_tier":"high","risk_pct":1.0},
 "gross_pnl":245.30,"net_pnl":187.40,"n_trades":35,"warnings":[]}
```

**Comportamento:**
- Ativo independentemente de `--realistic` (registra também execuções não-realistas)
- Append no final de cada `run()` — falha de escrita nunca interrompe o backtest
- Diretório de saída: mesmo de `backtest_results/` ou configurável via `BACKTEST_LOG_DIR`
- Rate-limit: máximo 1 linha por segundo (evita flood em loops automatizados)

### 5.6 Runner CLI — flags

```
python -m src.backtest.runner --symbol BTCUSDT --timeframe 4h --realistic
python -m src.backtest.runner --symbol ADAUSDT --timeframe 4h --realistic --override-slippage 0.002
python -m src.backtest.runner --symbol BTCUSDT --timeframe 4h  # modo legado
```

| Flag | Tipo | Default | Descrição |
|------|------|---------|-----------|
| `--realistic` | flag | `False` | Ativa RiskManager + custos |
| `--override-slippage` | `float` | — | Sobrescreve slippage do tier (gera WARN no log) |

### 5.7 API — query params

```
GET /backtest?symbol=BTCUSDT&timeframe=4h&realistic=true
GET /backtest?symbol=ADAUSDT&timeframe=4h&realistic=true&slippage_override=0.002
```

| Parâmetro | Tipo | Default | Descrição |
|-----------|------|---------|-----------|
| `realistic` | `bool` | `false` | Ativa RiskManager + custos |
| `slippage_override` | `float` | — | Sobrescreve slippage do tier (gera WARN no log) |

**Resposta 200 (realistic=true):**

```json
{
  "gross": { "total_pnl_usdt": 245.30, "win_rate_pct": 62.0, ... },
  "net": { "total_pnl_usdt": 187.40, "win_rate_pct": 62.0, ... },
  "warnings": [
    "IC 95% win rate: [44.2%, 76.8%] — N=35 < 50, baixa significância",
    "Razão net/gross: 0.76 — saudável (> 0.5)"
  ],
  "total_fees_usdt": 42.10,
  "total_slippage_usdt": 15.80,
  "generated_at": "2026-05-10T14:00:00Z"
}
```

---

## 6. Invariantes

| ID | Invariante |
|----|-----------|
| INV-028-01 | `pnl_net_usdt` nunca é maior que `pnl_gross_usdt` para o mesmo trade |
| INV-028-02 | Slippage mínimo = 0.0 (após clamp) |
| INV-028-03 | Taxa nunca excede o valor da posição (max 100%) |
| INV-028-04 | `--realistic` não altera trades gerados — só custos + sizing |
| INV-028-05 | Sem `--realistic`: `gross == net`, engine = comportamento SPEC_011 |
| INV-028-06 | Alerta informacional nunca bloqueia execução — exit code 0 sempre |
| INV-028-07 | Cada execução append em `backtest_runs.jsonl` com parâmetros + resultado |

---

## 7. Testes

| ID | Descrição |
|----|-----------|
| TEST_028_01 | Trade long realistic: entry_price sobe com slippage, PnL líquido < bruto |
| TEST_028_02 | Trade short realistic: entry_price desce com slippage, PnL líquido < bruto |
| TEST_028_03 | Slippage = 0 (override) → PnL líquido = bruto − taxas |
| TEST_028_04 | `realistic=false` → mesmo comportamento de antes (compatibilidade reversa) |
| TEST_028_05 | API com `realistic=true` retorna campos gross/net distintos |
| TEST_028_06 | PnL com RiskManager difere da fórmula linear no mesmo cenário |
| TEST_028_07 | Alerta de baixa significância aparece quando N < 50 |
| TEST_028_08 | Alerta de degradação alta aparece quando net/gross < 0.5 |
| TEST_028_09 | Alerta informacional não bloqueia execução (exit code 0) |
| TEST_028_10 | `backtest_runs.jsonl` recebe linha a cada execução |
| TEST_028_11 | Slippage override gera WARN no log |


---

## 8. Arquivos

| Arquivo | Mudança |
|---------|---------|
| `docs/SDD/SPEC_028_REALISMO_BACKTEST/SPEC.md` | Revisado — v2.0 |
| `src/config/settings.py` | Modificado — `BACKTEST_SLIPPAGE_BY_LIQ`, `BACKTEST_SLIPPAGE_LIQ_MAP`, `BACKTEST_MAKER_FEE`, `BACKTEST_TAKER_FEE`. Removido `BACKTEST_SLIPPAGE_FLAT`, `BACKTEST_SLIPPAGE_PCT`. |
| `src/backtest/engine.py` | Modificado — `__init__` recebe `RiskManager`, `_apply_costs`, `_build_warnings`, `_log_backtest_run`, PnL condicional |
| `src/backtest/models.py` | Modificado — novos campos `BacktestTrade`, `BacktestResult` com gross/net/warnings |
| `src/backtest/runner.py` | Modificado — `--realistic`, `--override-slippage` |
| `src/api/routes/backtest.py` | Modificado — query params `realistic`, `slippage_override` |
| `tests/backtest/test_spec028.py` | Criado — 33 testes (TEST_028_01 a 11 + unitários) |

---

## 9. Definition of Done

- [x] `_apply_costs` implementado com slippage por tier e taxas (INV-028-01 a 03)
- [x] `RiskManager` integrado ao `BacktestEngine` via `--realistic` (INV-028-04 a 05)
- [x] CLI `--realistic` funcional com saída Gross/Net + alerta informacional
- [x] API `GET /backtest?realistic=true` retornando gross/net/warnings
- [x] Logging de parâmetros ativo (`backtest_runs.jsonl` append)
- [x] TEST_028_01 a 11 (33 testes) passando
- [x] `ruff check src/ tests/` limpo nos arquivos alterados
- [x] `pytest tests/backtest/test_engine.py` sem falhas (compatibilidade SPEC_011 mantida)
