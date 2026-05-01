# SPEC — Especificação Técnica Completa — Binance Phicube

**Versão:** 1.0
**Data:** 2026-05-01
**Tipo:** Especificação Executável
**Audiência:** Backend Engineers, Quant Developers, QA Engineers

**Escopo Operacional (alinhado ao PRD e Manifesto):**

- Uso pessoal, instância única, um único operador.
- Corretora alvo: Binance Futures USDT-M.
- Não é plataforma multi-usuário.

---

## 1. Visão Arquitetural

### 1.1 Estrutura Geral

```text
┌─────────────────────────────────────────────────────────┐
│                    TRADING MONITOR                       │
│  (main.py: loop assíncrono, orquestra componentes)      │
└────────────────────┬────────────────────────────────────┘
                     │
     ┌───────────────┼───────────────┐
     │               │               │
     v               v               v
┌─────────────┐  ┌──────────────┐  ┌──────────────┐
│   EXCHANGE  │  │    SIGNAL    │  │     RISK     │
│  (ccxt)     │  │   ENGINE     │  │   MANAGER    │
│             │  │              │  │              │
│ - connect   │  │ - evaluate() │  │ - calculate()│
│ - OHLCV     │  │ - direction  │  │ - position   │
│ - order()   │  │ - entry/SL/TP│  │ - qty limit  │
│ - balance   │  │              │  │              │
└──────┬──────┘  └──────┬───────┘  └──────┬───────┘
       │                │                 │
       └────────────────┼─────────────────┘
                        │
                   ┌────v────────┐
                   │    ORDER    │
                   │   MANAGER   │
                   │             │
                   │ - execute() │
                   │ - SL/TP     │
                   └────┬────────┘
                        │
                   ┌────v────────────┐
                   │   STORAGE       │
                   │ (MongoDB/motor) │
                   │                 │
                   │ - save_trade    │
                   │ - save_signal   │
                   │ - audit_log     │
                   └─────────────────┘
                        │
                   ┌────v────────────┐
                   │    LOGGER       │
                   │  (structlog)    │
                   │                 │
                   │ - JSON stdout   │
                   │ - file (dev)    │
                   └─────────────────┘
```

### 1.2 Fluxo de Dados Principal (1 tick)

```text
TradingMonitor._tick()
    │
    ├─ fetch OHLCV (drop last candle)
    │   └─ ExchangeClient.fetch_ohlcv_with_retry()
    │
    ├─ check max_open_positions
    │
    ├─ check symbol already in open trade
    │
    ├─ evaluate signal
    │   └─ SignalEngine.evaluate(symbol, timeframe, df)
    │       └─ indicators.compute_all(df)
    │
    ├─ save signal (se detectado)
    │   └─ MongoRepository.save_signal()
    │
    ├─ calculate position (se sinal)
    │   └─ RiskManager.calculate(signal, balance)
    │
    ├─ execute trade (se posição viável)
    │   └─ OrderManager.execute(signal, position)
    │       ├─ ExchangeClient.set_leverage()
    │       ├─ ExchangeClient.create_market_order()
    │       ├─ ExchangeClient.create_stop_loss_order()
    │       └─ ExchangeClient.create_take_profit_order()
    │
    ├─ save trade
    │   └─ MongoRepository.save_trade()
    │
    └─ audit log
        └─ MongoRepository.audit()
```

---

## 2. Especificação de Componentes

### 2.1 Signal Engine (`src/strategy/signal_engine.py`)

#### Responsabilidade

Detectar sinais de entrada (LONG/SHORT) baseado em indicadores: Alligator, Awesome Oscillator, Fractais.

#### Interface Pública

```python
class Direction(Enum):
    LONG = "long"
    SHORT = "short"

@dataclass(frozen=True)
class Signal:
    symbol: str
    timeframe: str
    direction: Direction
    entry_price: float
    stop_loss: float
    take_profit: float
    fractal_ref: float  # Reference fractal (high/low)
    detected_at: datetime

    @property
    def risk(self) -> float:
        """Risk em valor absoluto: entry - SL"""
        return self.entry_price - self.stop_loss

    @property
    def reward(self) -> float:
        """Reward em valor absoluto: TP - entry"""
        return self.take_profit - self.entry_price

    @property
    def risk_reward_ratio(self) -> float:
        """RRR = reward / risk"""
        if self.risk == 0:
            return 0
        return self.reward / self.risk

class SignalEngine:
    def evaluate(self, symbol: str, timeframe: str, df: pd.DataFrame) -> Signal | None:
        """
        Detecta sinal na última candle fechada.

        Args:
            symbol: Ex. "BTCUSDT"
            timeframe: Ex. "4h"
            df: DataFrame com colunas OHLCV + indicadores computados

        Returns:
            Signal se detectado, None caso contrário

        Pré-requisito:
            - df deve ter >= 50 linhas (mínimo para indicadores)
            - indicadores já computados (alligator, ao, fractais)

        Contrato (invariantes):
            - Nunca retorna sinal na última candle (aguarda fechamento)
            - Sempre valida Alligator, AO, Fractais SIMULTANEAMENTE
            - SL nunca é zero
            - TP sempre > entry para LONG, sempre < entry para SHORT
        """
```

#### Regras Lógicas (LONG)

```text
Condições (TODAS devem ser verdadeiras):
1. Alligator bullish: lips > teeth > jaw (últimas 3 barras)
2. Awesome Oscillator > 0 (última barra)
3. Close > max(lips, teeth, jaw) (última barra)
4. Fractal bullish válido nos últimos 100 candles
   └─ Fractal = 5 barras onde alta central é maior que vizinhos
   └─ Máximo 2 últimas barras excluídas
   └─ Usar o fractal bullish mais recente (index > anterior)

Cálculo de SL e TP (LONG):
  SL = fractal_low (da última detecção)
  entry_price = close (última barra)
  TP = entry_price + (entry_price - SL) * RRR
```

#### Regras Lógicas (SHORT) — Inverso de LONG

```text
Condições (TODAS devem ser verdadeiras):
1. Alligator bearish: lips < teeth < jaw
2. Awesome Oscillator < 0
3. Close < min(lips, teeth, jaw)
4. Fractal bearish válido

Cálculo de SL e TP (SHORT):
  SL = fractal_high (da última detecção)
  entry_price = close
  TP = entry_price - (SL - entry_price) * RRR
```

#### Checklist de Implementação

- [ ] Pré-requisito validado: df.shape[0] >= 50
- [ ] Alligator verificado com ordem correta (lips > teeth > jaw)
- [ ] AO verificado como > 0 (LONG) ou < 0 (SHORT)
- [ ] Fractal bullish/bearish detectado (5 barras, índice máximo)
- [ ] SL, TP, entry calculados sem divisão por zero
- [ ] Sinal não retornado na candle "em progresso" (apenas fechada)
- [ ] Teste: 10+ históricos reais validados manualmente

---

### 2.2 Risk Manager (`src/trading/risk_manager.py`)

#### Responsabilidade

Calcular tamanho de posição baseado em risco controlado, respeitando limites de alavancagem e capital.

#### Interface Pública

```python
@dataclass(frozen=True)
class PositionSize:
    quantity: float  # Quantidade de cripto a comprar/vender
    risk: float     # Em USDT
    reward: float   # Em USDT
    risk_reward_ratio: float
    margin_used: float  # % do saldo utilizado

class RiskManager:
    def calculate(self,
                 signal: Signal,
                 available_balance: float,
                 quantity_precision: int = 3) -> PositionSize | None:
        """
        Calcula tamanho de posição para risco controlado.

        Args:
            signal: Signal com entry, SL, TP já computados
            available_balance: Saldo USDT disponível
            quantity_precision: Casas decimais da quantidade

        Returns:
            PositionSize se viável, None se violaria limites

        Contrato (invariantes):
            - Quantidade sempre > 0 e respeitando precision
            - Risco nunca excede risk_per_trade_pct
            - Margin usado nunca excede max_capital_allocation_pct
            - Nunca abre posição se max_open_positions já atingido
            - RRR sempre >= configurado
        """
```

#### Fórmula de Cálculo

```text
1. Risk amount (USDT):
   risk_amount = available_balance * (risk_per_trade_pct / 100)
   Ex: balance=1000, risk_pct=1% → risk_amount = 10 USDT

2. Stop distance (em cripto):
   stop_distance = |entry_price - stop_loss|

3. Quantidade base:
   qty_base = risk_amount / stop_distance
   Ex: risk=10, stop_distance=0.5 → qty_base = 20 BTC

4. Margin requerido (Futures):
   margin_required = (entry_price * qty_base) / leverage
   Ex: entry=50000, qty=0.2, leverage=5 → margin = 2000 USDT

5. Scale down se excede limite:
   Se margin_required > (balance * max_capital_allocation_pct):
      scale_factor = (balance * max_capital_allocation_pct) / margin_required
      qty = qty_base * scale_factor

6. Redondear para precision:
   qty = round(qty, quantity_precision)

7. Validações finais:
   - qty > 0
   - signal.risk_reward_ratio >= config.risk_reward_ratio
   - count_open_positions() < config.max_open_positions
   - margin_used <= max_capital_allocation_pct
```

#### Checklist de Implementação

- [ ] Fórmula implementada exatamente como acima
- [ ] Scale-down aplicado se margin > limite
- [ ] Validação de limites (max_open_positions, max_capital_allocation_pct)
- [ ] RRR mínimo respeitado
- [ ] Teste: 50 cenários (diferentes balanços, stops, leverages)

---

### 2.3 Order Manager (`src/trading/order_manager.py`)

#### Responsabilidade

Executar operação atomicamente: entrada → stop loss → take profit, com rollback se falhar.

#### Interface Pública

```python
class TradeStatus(Enum):
    ENTRY_PENDING = "entry_pending"
    ENTRY_EXECUTED = "entry_executed"
    STOP_LOSS_SET = "stop_loss_set"
    TAKE_PROFIT_SET = "take_profit_set"
    ACTIVE = "active"
    CLOSED_BY_SL = "closed_by_sl"
    CLOSED_BY_TP = "closed_by_tp"
    CLOSED_MANUAL = "closed_manual"
    FAILED = "failed"

@dataclass(frozen=True)
class Trade:
    entry_order_id: str  # ID único da order de entrada
    symbol: str
    direction: Direction
    entry_price: float
    stop_loss_price: float
    take_profit_price: float
    quantity: float
    status: TradeStatus
    created_at: datetime
    closed_at: datetime | None = None

    # IDs de ordens (pode ser None se não executadas)
    stop_loss_order_id: str | None = None
    take_profit_order_id: str | None = None

    # Resultado final
    exit_price: float | None = None
    pnl_usdt: float | None = None  # Lucro/prejuízo em USDT

class OrderManager:
    def execute(self,
               signal: Signal,
               position: PositionSize) -> Trade | None:
        """
        Executa operação: entrada → SL → TP

        Args:
            signal: Signal com entry, SL, TP
            position: PositionSize com quantidade

        Returns:
            Trade se todas as 3 ordens executadas, None se falha

        Contrato (invariantes):
            - Trade nunca fica em estado indefinido
            - Se qualquer ordem falha, cancel_all e retorna FAILED
            - Stop loss SEMPRE executado antes de retornar (nunca skip)
            - entry_order_id é único (previne duplicação)
            - SL sempre reduceOnly (nunca abre nova posição)
            - TP sempre reduceOnly
        """
```

#### Fluxo de Execução

```text
1. Set Leverage
   └─ ExchangeClient.set_leverage(signal.symbol, config.leverage)
      └─ Se erro: return None (não abre posição)

2. Set Margin Mode
   └─ ExchangeClient.set_margin_mode(symbol, "isolated")
      └─ Se erro: return None

3. Market Order (Entrada)
   └─ order = ExchangeClient.create_market_order(
        symbol, signal.direction, position.quantity
      )
      └─ Se erro: return None
      └─ Armazenar entry_order_id = order['id']
      └─ entry_price = order['average']

4. Stop Loss Order
   └─ sl_order = ExchangeClient.create_stop_loss_order(
        symbol, side=OPPOSITE(direction),
        stop_price=signal.stop_loss,
        quantity=position.quantity,
        reduceOnly=True
      )
      └─ Se erro:
         ├─ cancel_all_orders(symbol)
         ├─ trade.status = FAILED
         └─ return trade
      └─ Armazenar stop_loss_order_id = sl_order['id']

5. Take Profit Order
   └─ tp_order = ExchangeClient.create_take_profit_order(
        symbol, side=OPPOSITE(direction),
        limit_price=signal.take_profit,
        quantity=position.quantity,
        reduceOnly=True
      )
      └─ Se erro:
         ├─ cancel_all_orders(symbol)
         ├─ trade.status = FAILED
         └─ return trade
      └─ Armazenar take_profit_order_id = tp_order['id']

6. Retornar Trade
   └─ trade.status = ACTIVE
   └─ Salvar em MongoDB
```

#### Checklist de Implementação

- [ ] Set leverage antes de ordem
- [ ] Set margin mode (isolated)
- [ ] Market order com entry_order_id único
- [ ] Rollback (cancel_all) se SL falha
- [ ] Rollback se TP falha
- [ ] TradeStatus reflete estado real
- [ ] Teste: 20 cenários (sucesso, SL fail, TP fail)

---

### 2.4 Exchange Integration (`src/exchange/binance_client.py`)

#### Responsabilidade

Comunicação assíncrona com Binance (via ccxt), com retry e tratamento de erros.

#### Interface Pública

```python
class BinanceClient:
    async def connect(self) -> None:
        """Inicializa conexão ccxt"""

    async def close(self) -> None:
        """Fecha conexão"""

    async def fetch_ohlcv(self, symbol: str, timeframe: str,
                         limit: int = 200) -> pd.DataFrame:
        """
        Retorna OHLCV em DataFrame (sem última candle "em progresso")

        Contrato:
            - Nunca inclui candle atual (em progresso)
            - Retorna >= limit linhas ou erro
        """

    async def fetch_ohlcv_with_retry(self, symbol: str, timeframe: str,
                                     retries: int = 3) -> pd.DataFrame:
        """Idem, com retry exponencial"""

    async def fetch_usdt_balance(self) -> float:
        """Retorna saldo USDT disponível"""

    async def fetch_open_positions(self) -> list[dict]:
        """Retorna posições abertas (Futures)"""

    async def set_leverage(self, symbol: str, leverage: int) -> None:
        """Define alavancagem (Futures)"""

    async def set_margin_mode(self, symbol: str, mode: str) -> None:
        """Define "isolated" ou "cross" (Futures)"""

    async def create_market_order(self, symbol: str, side: str,
                                 quantity: float) -> dict:
        """Executa order de mercado (LONG=buy, SHORT=sell)"""

    async def create_stop_loss_order(self, symbol: str, side: str,
                                    stop_price: float, quantity: float,
                                    reduceOnly: bool = True) -> dict:
        """Executa STOP_MARKET order"""

    async def create_take_profit_order(self, symbol: str, side: str,
                                      limit_price: float, quantity: float,
                                      reduceOnly: bool = True) -> dict:
        """Executa TAKE_PROFIT_MARKET order"""

    async def cancel_all_orders(self, symbol: str) -> None:
        """Cancela todas as ordens abertas do símbolo"""

    def round_quantity(self, symbol: str, quantity: float) -> float:
        """Arredonda quantidade para precisão permitida"""

    def round_price(self, symbol: str, price: float) -> float:
        """Arredonda preço para tick size"""
```

#### Tratamento de Erros

```text
Erros recuperáveis (retry 3x com backoff exponencial):
  - Rate limit (429)
  - Timeout de rede
  - Indisponibilidade temporária

Erros fatais (falha imediata):
  - Chave inválida (401)
  - Saldo insuficiente
  - Symbol não existe
  - Quantidade/preço inválido
```

#### Checklist de Implementação

- [ ] Async/await sem threads
- [ ] Retry com backoff exponencial (1s, 2s, 4s)
- [ ] Testnet vs. Produção via env var
- [ ] round_quantity e round_price respeitam limites da exchange
- [ ] Teste: Testnet 50 operações com sucesso

---

### 2.5 Storage Layer (`src/storage/repository.py`)

#### Responsabilidade

Persistência em MongoDB (assíncrona via motor), com indexação e auditoria.

#### Interface Pública

```python
class MongoRepository:
    async def setup_indexes(self) -> None:
        """Cria índices obrigatórios na inicialização"""

    async def save_signal(self, signal: Signal) -> None:
        """Persiste sinal em collection 'signals'"""

    async def save_trade(self, trade: Trade) -> None:
        """Persiste trade em collection 'trades' (com índice em entry_order_id)"""

    async def update_trade_status(self, entry_order_id: str,
                                  status: TradeStatus) -> None:
        """Atualiza status de trade (ex: ACTIVE → CLOSED_BY_SL)"""

    async def get_open_trades(self) -> list[Trade]:
        """Retorna trades com status ACTIVE"""

    async def get_open_trades_for_symbol(self, symbol: str) -> list[Trade]:
        """Retorna trades ACTIVE de um símbolo específico"""

    async def count_open_positions(self) -> int:
        """Retorna quantidade de trades ACTIVE"""

    async def audit(self, event: str, details: dict) -> None:
        """Registra evento de auditoria em collection 'audit_log'"""
```

#### Esquema MongoDB

```javascript
// Collection: signals
{
  _id: ObjectId(),
  symbol: "BTCUSDT",
  timeframe: "4h",
  direction: "long",
  entry_price: 50000.0,
  stop_loss: 49000.0,
  take_profit: 52000.0,
  detected_at: ISODate("2026-05-01T10:00:00Z"),
  created_at: ISODate("2026-05-01T10:00:00Z")
}

// Collection: trades (com índice único em entry_order_id)
{
  _id: ObjectId(),
  entry_order_id: "123456789",  // Índice ÚNICO
  symbol: "BTCUSDT",
  direction: "long",
  entry_price: 50000.0,
  stop_loss_price: 49000.0,
  take_profit_price: 52000.0,
  quantity: 0.02,
  status: "active",
  created_at: ISODate("2026-05-01T10:00:00Z"),
  closed_at: null,
  stop_loss_order_id: "987654321",
  take_profit_order_id: "987654322",
  exit_price: null,
  pnl_usdt: null
}

// Collection: audit_log
{
  _id: ObjectId(),
  event: "trade_opened",
  details: {
    entry_order_id: "123456789",
    reason: "BO Williams signal detected"
  },
  timestamp: ISODate("2026-05-01T10:00:00Z")
}
```

#### Checklist de Implementação

- [ ] Motor async configurado
- [ ] Índices criados em setup (entry_order_id único)
- [ ] Operações UPSERT para evitar duplicação
- [ ] Teste: 100 inserts, queries, updates

---

### 2.6 Logger (`src/monitoring/logger.py`)

#### Responsabilidade

Logging estruturado (JSON em produção, console em dev).

#### Interface Pública

```python
def configure_logging(log_level: str) -> None:
    """Configura structlog com nível desejado"""

def get_logger(name: str) -> logging.Logger:
    """Retorna logger configurado"""

# Uso:
logger = get_logger(__name__)
logger.info("sinal detectado", symbol="BTCUSDT", direction="long")
# Em produção, output é JSON (parsável)
# Em dev, output é console colorido
```

#### Eventos Obrigatórios

```python
# Signal Engine
logger.info("signal_detected", symbol, timeframe, direction, entry, sl, tp)

# Risk Manager
logger.info("position_calculated", symbol, quantity, risk, reward, rrr)
logger.warning("position_rejected", reason)  # Se violou limite

# Order Manager
logger.info("order_entry_executed", symbol, entry_order_id, price)
logger.info("order_sl_executed", symbol, stop_loss_order_id, price)
logger.info("order_tp_executed", symbol, take_profit_order_id, price)
logger.error("order_failed", symbol, reason)

# Exchange
logger.info("api_request", endpoint, method, symbol)
logger.warning("api_retry", endpoint, attempt, next_wait_ms)
logger.error("api_error", endpoint, error_code, error_msg)

# Storage
logger.info("record_saved", collection, count)
logger.error("record_save_failed", collection, error)

# Monitor
logger.info("tick", open_positions_count, balance_usdt)
```

#### Checklist de Implementação

- [ ] JSON output em produção (TTY check)
- [ ] Console output colorido em dev
- [ ] Todos os eventos acima logados
- [ ] Sem exposição de chaves em logs

---

## 3. Padrões de Design

### 3.1 Async/Await Obrigatório

Todas as operações I/O são assíncronas:

- ❌ NÃO usar threads
- ✅ SIM usar `async def`, `await`, `asyncio.gather()`

```python
async def main():
    tasks = [
        fetch_ohlcv("BTCUSDT", "4h"),
        fetch_ohlcv("ETHUSDT", "4h"),
    ]
    results = await asyncio.gather(*tasks)
```

### 3.2 Imutabilidade de Dataclasses

Todas as entidades (Signal, Trade, PositionSize) são `frozen=True`:

```python
@dataclass(frozen=True)
class Signal:
    symbol: str
    # ...

# ❌ Não pode fazer:
signal.symbol = "other"

# ✅ Cria nova instância:
new_signal = Signal(symbol="other", ...)
```

### 3.3 Type Hints Completos

```python
# ❌ Ruim
def evaluate(df):
    return signal

# ✅ Bom
def evaluate(self, df: pd.DataFrame) -> Signal | None:
    return signal
```

### 3.4 Error Handling Explícito

```python
try:
    order = await exchange.create_market_order(...)
except BinanceAPIError as e:
    logger.error("order_failed", error_code=e.code, message=e.message)
    # Rollback
    await exchange.cancel_all_orders(symbol)
    raise
```

---

## 4. Fluxo de Execução Detalhado

### 4.1 Inicialização (startup)

```python
async def main():
    # 1. Configuração
    settings = load_settings()
    logger = get_logger(__name__)

    # 2. Conexão com Binance
    exchange = BinanceClient(settings)
    await exchange.connect()

    # 3. Conexão com MongoDB
    repo = MongoRepository(settings)
    await repo.setup_indexes()

    # 4. Iniciar monitor
    monitor = TradingMonitor(exchange, repo, settings)

    # 5. Loop infinito
    await monitor.run()
```

### 4.2 Um Tick (1 min ou 1 min, conforme timeframe)

```text
_tick():
  1. FETCH OHLCV (drop última candle)
  2. CHECK max_open_positions
  3. LOOP por cada símbolo:
       a. CHECK já em trade
       b. EVALUATE sinal
       c. SAVE sinal (se detectado)
       d. CALCULATE posição (se sinal)
       e. EXECUTE trade (se posição viável)
       f. SAVE trade
       g. AUDIT log
  4. WAIT (até próximo tick)
```

---

## 5. Testes e Validação

### 5.1 Cobertura Mínima

- Signal Engine: 100% (signal detection é crítico)
- Risk Manager: 95% (cálculo de posição)
- Order Manager: 90% (execução com mocking)
- Exchange: 80% (mocking de API)

### 5.2 Teste de Sinal (Exemplo)

```python
def test_long_signal_detection():
    df = load_historical("BTCUSDT", "4h", "2024-01-01", "2024-12-31")
    engine = SignalEngine()

    # Candle com sinal válido
    signal = engine.evaluate("BTCUSDT", "4h", df.iloc[-1:])
    assert signal is not None
    assert signal.direction == Direction.LONG
    assert signal.entry_price == df.iloc[-1]["close"]
    assert signal.stop_loss < signal.entry_price
    assert signal.take_profit > signal.entry_price
    assert signal.risk_reward_ratio >= 2.0
```

### 5.3 Teste de Posição (Exemplo)

```python
def test_position_sizing():
    signal = Signal(...)
    balance = 1000.0

    position = RiskManager().calculate(signal, balance)

    assert position.quantity > 0
    assert position.risk == balance * 0.01  # 1% risk
    margin_used = (signal.entry_price * position.quantity) / 5
    assert margin_used <= balance * 0.30  # 30% max allocation
```

---

## 6. Checklist de Code Review

### Para Toda PR

- [ ] Tipo hints completos (sem `Any`)
- [ ] Async/await correto (sem threads)
- [ ] Dataclasses frozen onde aplicável
- [ ] Logging estruturado presente
- [ ] Testes passando (80%+ cobertura)
- [ ] Nenhuma chave hardcoded
- [ ] Contrato em SPEC.md respeitado

### Para Signal Engine

- [ ] Alligator validado: lips > teeth > jaw
- [ ] AO validado: > 0 (LONG) ou < 0 (SHORT)
- [ ] Fractal detectado: 5-candle pattern
- [ ] SL, TP calculados sem divisão por zero
- [ ] Teste manual vs. histórico: 10+ setups

### Para Risk Manager

- [ ] Fórmula de risco exata
- [ ] Scale-down aplicado se necessário
- [ ] max_open_positions respeitado
- [ ] max_capital_allocation_pct respeitado
- [ ] Teste: 50 cenários diferentes

### Para Order Manager

- [ ] Leverage + margin mode antes de ordem
- [ ] Rollback (cancel_all) se falha
- [ ] entry_order_id único (previne duplicação)
- [ ] reduceOnly em SL e TP
- [ ] TradeStatus reflete estado real

---

## 7. Versionamento e Evolução

### 7.1 Quando Mudar SPEC

- **Novo componente:** Adicionar seção 2.X
- **Nova regra lógica:** Atualizar regras (ex: 2.1)
- **Novo contrato:** Adicionar a Interface Pública

### 7.2 Comunicação de Mudanças

```text
Commit message:
feat(spec): add fraud detection to Signal Engine

Updated: SDD/SPEC.md § 2.1 (Signal Engine)
Added: New rule to reject signals on low volume
Impact: ✅ Low-risk, additive only

Refs: PRD.md § Risks (Whipsaw detection)
```

---

**SPEC.md é a verdade executável. Todo código deve conformar a isto.**

*Mantido por: Backend Sênior + Quant Developer*
*Governado por: Time A + Risk Manager*
*Última atualização: 2026-05-01*
