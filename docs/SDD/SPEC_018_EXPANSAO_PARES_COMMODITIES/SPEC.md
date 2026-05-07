# SPEC_018 — Expansão de Pares: Commodities (XPTUSDT e COPPERUSDT)

**ID:** SPEC_018
**Título:** Expansão de Pares — Commodities Tokenizadas (Platinum e Copper)
**Status:** Concluída
**Data:** 2026-05-06
**Autor:** Time A (Refinamento)
**Revisores:** Trader Sênior · Risk Manager · Quant Developer

---

## 1. Objetivo

Adicionar **XPTUSDT** (Platinum) e **COPPERUSDT** (Copper) ao bot como pares de commodities tokenizadas na Binance Futures USDT-M.

O escopo inclui:

1. Migrar a configuração de pares do produto cartesiano `SYMBOLS × TIMEFRAMES` para triplets explícitos `symbol:timeframe:leverage`.
2. Implementar validação de liquidez mínima em startup para cada par.
3. Corrigir o bug em `TradingMonitor._interval` (hardcoded 300 s, ignora timeframe).
4. Garantir que commodities operem em 1h com alavancagem 3x.

---

## 2. Contexto e Motivação

### 2.1 Estado Atual

- `Settings.SYMBOLS: list[str]` e `Settings.TIMEFRAMES: list[str]` geram produto cartesiano.
- `TradingMonitor._interval` = 300 s fixo, independente do timeframe — bug para pares 1h.
- Não há validação de liquidez em startup; pares ilíquidos podem ser carregados silenciosamente.

### 2.2 Motivação de Negócio

- Platinum e Copper têm correlação diferenciada com cripto, diversificando o portfólio.
- Commodities exigem alavancagem conservadora (3x) vs. cripto (5x).
- Commodities operam melhor em 1h; cripto em 15m — o produto cartesiano impossibilita isso.

### 2.3 Decisões de Especialistas

| Especialista | Decisão |
|---|---|
| Trader Sênior | Método BO Williams aplicável a commodities; 1h recomendado; backtest obrigatório antes de produção |
| Risk Manager | Alavancagem 3x para commodities; `max_capital_allocation_pct` ≤ 20%; gate `COMMODITIES_BACKTEST_VALIDATED=true` |
| Quant Developer | Precisão decimal via `fetch_quantity_precision_map()`; volume mínimo 500k USDT; OI mínimo 200k USDT |

---

## 3. User Stories e Critérios de Aceite

### US-018-01 — Configuração por Triplet

**Como** operador, **quero** configurar pares como `BTCUSDT:15m:5,XPTUSDT:1h:3` **para** cada par ter seu próprio timeframe e alavancagem.

**Gherkin:**
```gherkin
Scenario: Parse de triplet válido
  Given SYMBOL_TIMEFRAMES="BTCUSDT:15m:5,XPTUSDT:1h:3,COPPERUSDT:1h:3"
  When Settings é instanciada
  Then symbol_timeframes contém 3 SymbolConfig
  And SymbolConfig(symbol="XPTUSDT", timeframe="1h", leverage=3) está presente

Scenario: Triplet com formato inválido
  Given SYMBOL_TIMEFRAMES="BTCUSDT:15m"
  When Settings é instanciada
  Then ValidationError é levantado com mensagem "formato inválido"
```

### US-018-02 — Intervalo Correto por Timeframe

**Como** bot, **quero** que `TradingMonitor` calcule o intervalo de sleep a partir do timeframe do par **para** que pares 1h esperem 3600 s e pares 15m esperem 900 s.

**Gherkin:**
```gherkin
Scenario: Intervalo para 15m
  Given SymbolConfig(symbol="BTCUSDT", timeframe="15m", leverage=5)
  When TradingMonitor é instanciado
  Then _interval == 900

Scenario: Intervalo para 1h
  Given SymbolConfig(symbol="XPTUSDT", timeframe="1h", leverage=3)
  When TradingMonitor é instanciado
  Then _interval == 3600
```

### US-018-03 — Validação de Liquidez em Startup

**Como** bot, **quero** que pares com liquidez insuficiente sejam rejeitados no startup **para** evitar execuções em mercados ilíquidos.

**Gherkin:**
```gherkin
Scenario: Par com liquidez suficiente
  Given volume_24h=600_000 USDT e open_interest=300_000 USDT para XPTUSDT
  When validate_market_liquidity("XPTUSDT") é chamado
  Then retorna True

Scenario: Par com volume insuficiente
  Given volume_24h=400_000 USDT para COPPERUSDT
  When validate_market_liquidity("COPPERUSDT") é chamado
  Then levanta InsufficientLiquidityError com mensagem contendo "volume_24h"

Scenario: Par com OI insuficiente
  Given volume_24h=700_000 USDT e open_interest=100_000 USDT
  When validate_market_liquidity() é chamado
  Then levanta InsufficientLiquidityError com mensagem contendo "open_interest"
```

### US-018-04 — Alavancagem por Par

**Como** bot, **quero** que a alavancagem configurada no triplet seja aplicada via `set_leverage()` **para** commodities (3x) e cripto (5x) terem exposições corretas.

**Gherkin:**
```gherkin
Scenario: Leverage aplicada corretamente
  Given SymbolConfig(symbol="XPTUSDT", timeframe="1h", leverage=3)
  When TradingMonitor inicia
  Then set_leverage("XPTUSDT", 3) é chamado exatamente uma vez

Scenario: Leverage não é padrão global
  Given dois pares com leverages diferentes (3 e 5)
  When ambos iniciam
  Then cada um chama set_leverage com seu próprio valor
```

### US-018-05 — Gate de Produção para Commodities

**Como** risk manager, **quero** que commodities só operem se `COMMODITIES_BACKTEST_VALIDATED=true` **para** impedir live trading sem backtest aprovado.

**Gherkin:**
```gherkin
Scenario: Gate não configurado
  Given COMMODITIES_BACKTEST_VALIDATED não está definido (ou false)
  And symbol_timeframes contém XPTUSDT ou COPPERUSDT
  When Settings é instanciada
  Then ValidationError é levantado com mensagem "backtest não validado"

Scenario: Gate habilitado
  Given COMMODITIES_BACKTEST_VALIDATED=true
  When Settings é instanciada com XPTUSDT
  Then nenhum erro é levantado
```

---

## 4. Design de Arquitetura

### 4.1 `SymbolConfig` — Novo Dataclass

```python
# src/config/settings.py
from dataclasses import dataclass

@dataclass(frozen=True)
class SymbolConfig:
    symbol: str
    timeframe: str
    leverage: int

    @classmethod
    def from_triplet(cls, triplet: str) -> "SymbolConfig":
        """Parse 'BTCUSDT:15m:5' → SymbolConfig."""
        parts = triplet.strip().split(":")
        if len(parts) != 3:
            raise ValueError(f"Triplet inválido: {triplet!r} — formato esperado: SYMBOL:TIMEFRAME:LEVERAGE")
        symbol, timeframe, leverage_str = parts
        if not leverage_str.isdigit() or int(leverage_str) <= 0:
            raise ValueError(f"Leverage inválida em triplet: {triplet!r}")
        return cls(symbol=symbol.upper(), timeframe=timeframe, leverage=int(leverage_str))
```

### 4.2 `Settings` — Migração de Configuração

```python
class Settings(BaseSettings):
    # Substitui SYMBOLS + TIMEFRAMES + LEVERAGE
    SYMBOL_TIMEFRAMES: str = "BTCUSDT:15m:5,ETHUSDT:15m:5"

    # Gate de segurança para commodities
    COMMODITIES_BACKTEST_VALIDATED: bool = False

    # Risk
    MAX_CAPITAL_ALLOCATION_PCT: float = 0.20  # reduzido de 0.30

    @property
    def symbol_timeframes(self) -> list[SymbolConfig]:
        configs = [SymbolConfig.from_triplet(t) for t in self.SYMBOL_TIMEFRAMES.split(",")]
        commodities = {"XPTUSDT", "COPPERUSDT"}
        has_commodity = any(c.symbol in commodities for c in configs)
        if has_commodity and not self.COMMODITIES_BACKTEST_VALIDATED:
            raise ValueError(
                "Commodities detectadas em SYMBOL_TIMEFRAMES mas backtest não validado. "
                "Defina COMMODITIES_BACKTEST_VALIDATED=true após concluir backtest."
            )
        return configs
```

### 4.3 `TradingMonitor` — Correção de `_interval`

```python
_TIMEFRAME_SECONDS = {
    "1m": 60, "3m": 180, "5m": 300, "15m": 900,
    "30m": 1800, "1h": 3600, "2h": 7200, "4h": 14400,
    "6h": 21600, "8h": 28800, "12h": 43200, "1d": 86400,
}

class TradingMonitor:
    def __init__(self, config: SymbolConfig, ...):
        self._config = config
        self._interval = _TIMEFRAME_SECONDS.get(config.timeframe, 300)
        # BUG CORRIGIDO: antes era _interval = 300 fixo
```

### 4.4 `validate_market_liquidity()` — Nova Função

```python
# src/exchange/binance_client.py
LIQUIDITY_MIN_VOLUME_24H = 500_000   # USDT
LIQUIDITY_MIN_OPEN_INTEREST = 200_000  # USDT

async def validate_market_liquidity(
    self,
    symbol: str,
    min_volume: float = LIQUIDITY_MIN_VOLUME_24H,
    min_oi: float = LIQUIDITY_MIN_OPEN_INTEREST,
) -> None:
    """Levanta InsufficientLiquidityError se o par não atende mínimos."""
    ticker = await self._exchange.fetch_ticker(symbol)
    volume_24h = ticker.get("quoteVolume", 0.0)
    if volume_24h < min_volume:
        raise InsufficientLiquidityError(
            f"{symbol}: volume_24h={volume_24h:.0f} USDT < mínimo {min_volume:.0f}"
        )
    oi_data = await self._exchange.fetch_open_interest(symbol)
    oi = oi_data.get("openInterestValue", 0.0)
    if oi < min_oi:
        raise InsufficientLiquidityError(
            f"{symbol}: open_interest={oi:.0f} USDT < mínimo {min_oi:.0f}"
        )
```

### 4.5 `fetch_quantity_precision_map()` — Precisão Decimal

```python
async def fetch_quantity_precision_map(self, symbols: list[str]) -> dict[str, int]:
    """Retorna {symbol: casas_decimais} para cálculo de qty sem rejeição da exchange."""
    markets = await self._exchange.load_markets()
    return {
        s: markets[s]["precision"]["amount"]
        for s in symbols
        if s in markets
    }
```

### 4.6 Inicialização em `src/main.py`

```python
async def main():
    settings = get_settings()
    configs = settings.symbol_timeframes  # lista de SymbolConfig

    async with BinanceClient(settings) as client:
        # Validação de liquidez em startup
        for cfg in configs:
            await client.validate_market_liquidity(cfg.symbol)

        # Precisão decimal
        precision_map = await client.fetch_quantity_precision_map(
            [c.symbol for c in configs]
        )

        # Um TradingMonitor por triplet
        monitors = [
            TradingMonitor(cfg, client, precision_map[cfg.symbol], ...)
            for cfg in configs
        ]
        await asyncio.gather(*[m.run() for m in monitors])
```

### 4.7 `.env.example` — Novas Variáveis

```dotenv
# Substituem SYMBOLS e TIMEFRAMES
SYMBOL_TIMEFRAMES=BTCUSDT:15m:5,ETHUSDT:15m:5

# Gate de segurança: habilitar APENAS após backtest aprovado
COMMODITIES_BACKTEST_VALIDATED=false

# Reduzido para maior segurança com portfólio diversificado
MAX_CAPITAL_ALLOCATION_PCT=0.20
```

---

## 5. Invariantes de Risco

| ID | Invariante |
|---|---|
| INV-018-01 | Commodities nunca operam sem `COMMODITIES_BACKTEST_VALIDATED=true` |
| INV-018-02 | Alavancagem máxima para commodities: 3x |
| INV-018-03 | Liquidez validada em startup antes de qualquer ordem |
| INV-018-04 | `MAX_CAPITAL_ALLOCATION_PCT` ≤ 20% quando há commodities no portfólio |
| INV-018-05 | Stop-loss obrigatório para todos os pares (invariante já existente, reafirmada) |
| INV-018-06 | Precisão decimal por par — nunca usar valor hardcoded |

---

## 6. Testes

### 6.1 Unitários (`tests/config/test_symbol_config.py`)

```python
def test_from_triplet_valido():
    cfg = SymbolConfig.from_triplet("BTCUSDT:15m:5")
    assert cfg.symbol == "BTCUSDT"
    assert cfg.timeframe == "15m"
    assert cfg.leverage == 5

def test_from_triplet_formato_invalido():
    with pytest.raises(ValueError, match="formato inválido"):
        SymbolConfig.from_triplet("BTCUSDT:15m")

def test_from_triplet_leverage_zero():
    with pytest.raises(ValueError, match="Leverage inválida"):
        SymbolConfig.from_triplet("BTCUSDT:15m:0")

def test_settings_symbol_timeframes_parse():
    s = Settings(SYMBOL_TIMEFRAMES="BTCUSDT:15m:5,ETHUSDT:15m:5", ...)
    assert len(s.symbol_timeframes) == 2

def test_settings_commodity_sem_gate_levanta():
    with pytest.raises(ValueError, match="backtest não validado"):
        Settings(
            SYMBOL_TIMEFRAMES="XPTUSDT:1h:3",
            COMMODITIES_BACKTEST_VALIDATED=False,
        )

def test_settings_commodity_com_gate_ok():
    s = Settings(
        SYMBOL_TIMEFRAMES="XPTUSDT:1h:3",
        COMMODITIES_BACKTEST_VALIDATED=True,
    )
    assert s.symbol_timeframes[0].symbol == "XPTUSDT"

def test_trading_monitor_intervalo_15m():
    cfg = SymbolConfig(symbol="BTCUSDT", timeframe="15m", leverage=5)
    monitor = TradingMonitor(cfg, ...)
    assert monitor._interval == 900

def test_trading_monitor_intervalo_1h():
    cfg = SymbolConfig(symbol="XPTUSDT", timeframe="1h", leverage=3)
    monitor = TradingMonitor(cfg, ...)
    assert monitor._interval == 3600

def test_trading_monitor_intervalo_timeframe_desconhecido():
    cfg = SymbolConfig(symbol="XPTUSDT", timeframe="99m", leverage=3)
    monitor = TradingMonitor(cfg, ...)
    assert monitor._interval == 300  # fallback seguro
```

### 6.2 Unitários (`tests/exchange/test_liquidity.py`)

```python
async def test_validate_liquidity_ok(mock_client):
    mock_client.fetch_ticker.return_value = {"quoteVolume": 600_000}
    mock_client.fetch_open_interest.return_value = {"openInterestValue": 300_000}
    await client.validate_market_liquidity("XPTUSDT")  # sem exceção

async def test_validate_liquidity_volume_insuficiente(mock_client):
    mock_client.fetch_ticker.return_value = {"quoteVolume": 400_000}
    with pytest.raises(InsufficientLiquidityError, match="volume_24h"):
        await client.validate_market_liquidity("XPTUSDT")

async def test_validate_liquidity_oi_insuficiente(mock_client):
    mock_client.fetch_ticker.return_value = {"quoteVolume": 600_000}
    mock_client.fetch_open_interest.return_value = {"openInterestValue": 100_000}
    with pytest.raises(InsufficientLiquidityError, match="open_interest"):
        await client.validate_market_liquidity("XPTUSDT")

async def test_fetch_quantity_precision_map(mock_client):
    mock_client.load_markets.return_value = {
        "XPTUSDT": {"precision": {"amount": 2}},
        "BTCUSDT": {"precision": {"amount": 3}},
    }
    result = await client.fetch_quantity_precision_map(["XPTUSDT", "BTCUSDT"])
    assert result == {"XPTUSDT": 2, "BTCUSDT": 3}
```

### 6.3 Integração (`tests/integration/test_symbol_startup.py`)

```python
# Marcados @pytest.mark.integration — requerem BINANCE_TESTNET=True
async def test_startup_xptusdt_testnet():
    """Valida que XPTUSDT existe e passa validação de liquidez no testnet."""
    ...

async def test_startup_copperusdt_testnet():
    """Valida que COPPERUSDT existe e passa validação de liquidez no testnet."""
    ...

async def test_leverage_aplicada_xptusdt():
    """Verifica que set_leverage(XPTUSDT, 3) não levanta exceção."""
    ...

async def test_precision_map_commodities():
    """Verifica que fetch_quantity_precision_map retorna precisão > 0 para commodities."""
    ...
```

---

## 7. Task Graph (19 tarefas)

| # | Tarefa | Dependências | Responsável |
|---|---|---|---|
| T01 | Criar `SymbolConfig` dataclass + `from_triplet()` | — | backend-senior |
| T02 | Migrar `Settings` para `symbol_timeframes` property | T01 | backend-senior |
| T03 | Implementar gate `COMMODITIES_BACKTEST_VALIDATED` em `Settings` | T02 | risk-manager |
| T04 | Corrigir `TradingMonitor._interval` com `_TIMEFRAME_SECONDS` | T01 | backend-senior |
| T05 | Implementar `InsufficientLiquidityError` | — | backend-senior |
| T06 | Implementar `validate_market_liquidity()` | T05 | backend-senior |
| T07 | Implementar `fetch_quantity_precision_map()` | — | backend-senior |
| T08 | Atualizar inicialização em `src/main.py` | T02, T04, T06, T07 | backend-senior |
| T09 | Atualizar `.env.example` | T02 | backend-senior |
| T10 | Testes unitários `SymbolConfig` | T01 | backend-senior |
| T11 | Testes unitários `Settings` com gate | T03 | backend-senior |
| T12 | Testes unitários `TradingMonitor._interval` | T04 | backend-senior |
| T13 | Testes unitários `validate_market_liquidity()` | T06 | backend-senior |
| T14 | Testes unitários `fetch_quantity_precision_map()` | T07 | backend-senior |
| T15 | Remover `SYMBOLS` e `TIMEFRAMES` de `Settings` (breaking) | T08 | backend-senior |
| T16 | Testes integração testnet (marcados `@pytest.mark.integration`) | T08 | backend-senior |
| T17 | Backtest XPTUSDT 1h (fora do scope de código — operacional) | — | operador |
| T18 | Backtest COPPERUSDT 1h (fora do scope de código — operacional) | — | operador |
| T19 | Atualizar `docs/SDD/README.md` com SPEC_018 Concluída | T08 | backend-senior |

> **T17 e T18** são tarefas operacionais (não de código). Devem ser concluídas e documentadas antes de configurar `COMMODITIES_BACKTEST_VALIDATED=true` em produção.

---

## 8. Definição de Pronto (DoD)

- [ ] `SymbolConfig.from_triplet()` implementado e testado
- [ ] `Settings.symbol_timeframes` substitui `SYMBOLS × TIMEFRAMES`
- [ ] Gate `COMMODITIES_BACKTEST_VALIDATED` bloqueia startup sem backtest
- [ ] `TradingMonitor._interval` derivado do timeframe do par
- [ ] `validate_market_liquidity()` valida volume e OI em startup
- [ ] `fetch_quantity_precision_map()` retorna precisão por símbolo
- [ ] Todos os testes unitários passando (`pytest tests/config/ tests/exchange/ -v`)
- [ ] `ruff check src/ tests/` sem erros
- [ ] `.env.example` atualizado com novas variáveis
- [ ] SPEC_018 marcada como **Concluída** em `docs/SDD/README.md`

---

## 9. Notas Operacionais

### Backtest Obrigatório (INV-018-05)

Antes de definir `COMMODITIES_BACKTEST_VALIDATED=true` em qualquer ambiente (staging ou produção), o operador deve:

1. Executar `python tools/backtest_runner.py --symbol XPTUSDT --timeframe 1h --period 6m`
2. Executar `python tools/backtest_runner.py --symbol COPPERUSDT --timeframe 1h --period 6m`
3. Verificar que win rate ≥ 40% e profit factor ≥ 1.5
4. Documentar resultados em `docs/backtests/commodities_1h_YYYYMMDD.md`

### Horários de Mercado

- Platinum (XPT): mercado de futuros opera 23h/dia com pausa de 1h (22:00–23:00 ET)
- Copper (HG): idem
- A Binance Futures opera 24/7 nos tokens tokenizados; não há gap de horário

### Configuração Recomendada para Produção

```dotenv
SYMBOL_TIMEFRAMES=BTCUSDT:15m:5,ETHUSDT:15m:5,XPTUSDT:1h:3,COPPERUSDT:1h:3
COMMODITIES_BACKTEST_VALIDATED=true  # somente após backtest aprovado
MAX_CAPITAL_ALLOCATION_PCT=0.20
MAX_OPEN_POSITIONS=4
```

---

*SPEC_018 aprovada em 2026-05-06 com pareceres favoráveis de Trader Sênior, Risk Manager e Quant Developer.*
