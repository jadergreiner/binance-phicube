# Tasks — SPEC_043 Slippage Protection

**Artefatos relacionados:**
- `SPEC.md` — Especificação técnica v2.0 (596 linhas)
- `PRD_043.md` — Product Requirements v1.0 (258 linhas)
- `PLAN.md` — Plano de implementação v1.0 (691 linhas)

**Padrões de Design Aplicados:** State, Mediator, Observer, Decorator, Facade, Chain of Responsibility, Builder

---

## Validação de Consistência (Docs × AGENTS.md × Código)

### Issues Críticas Pós-Plano

| # | Issue | Origem | Impacto | Resolução |
|---|-------|--------|---------|-----------|
| V01 | **priceProtect fallback ausente para SL/TP comuns** — PRD D01 diz "fallback para stops comuns" mas PLAN U2.1 só adiciona `priceProtect: True` sem try/except | PRD D01 vs PLAN U2.1 | 🔴 **Crítico**: se exchange rejeitar priceProtect, ordem SL falha → posição sem stop → viola AGENTS.md "Risk-first: nenhuma posição abre sem SL já enviado" | PREMISSA: adicionar `try/except ccxt.BadRequest` em U2.1 (SL/TP), simétrico a U2.2 |
| V02 | **Callback type mismatch (sync vs async)** — PRD D08 define `Callable[[str, float], None]` (sync) mas `register_trade_outcome()` é `async def` com `asyncio.Lock`. OrderMonitor handlers são async e precisariam `await callback(...)`. | PRD D08, PLAN U7.2, SPEC §5.3 | 🟡 **Alto**: runtime `TypeError` se callback sync for invocado com `await`, ou `RuntimeWarning` se async for chamado sem `await` | PREMISSA: alterar tipo para `Callable[[str, float], Coroutine[Any, Any, None]]` e chamar com `await self._on_trade_closed(symbol, pnl_usdt)` |
| V03 | **`_map_risk_rejection_outcome` é função module-level, não método** — PLAN U7.3 trata como método de TradingMonitor mas `main.py:548` mostra função standalone sem `self` | PLAN U7.3 vs main.py:548 | 🟢 **Baixo**: correção na task — adicionar entradas no `mapping` dict, sem mudar assinatura | PREMISSA: adicionar `"SLIPPAGE_EXCEEDS_TOLERANCE"` e `"CIRCUIT_BREAKER_ACTIVE"` ao dict `mapping` |
| V04 | **RiskManager não importa `asyncio`** — PLAN U6.1 adiciona `asyncio.Lock` mas `risk_manager.py` atualmente não tem `import asyncio` | PLAN U6.1 vs risk_manager.py imports | 🟢 **Baixo**: adicionar `import asyncio` nas imports | PREMISSA: incluído na Task-011 |

### Issues Esclarecidas (Sem Ação)

| # | Issue | Status |
|---|-------|--------|
| V05 | `OrderMonitor.__init__` já tem 7 parâmetros — adicionar `on_trade_closed` como 8º é aceitável, todos opcionais exceto client/repo/notifier | ✅ Sem quebra |
| V06 | `max_position_pct=0` desabilita — PLAN U3.1 trata como `effective_max = min(MAX, balance * 0 / 100) = 0` → trava trades. Correto: se `pct=0`, ignorar (usar só MAX_POSITION_USDT) | ✅ Já especificado no DoD |
| V07 | Estrutura de testes espelha `src/` (AGENTS.md linha 86-87) — `tests/exchange/`, `tests/trading/`, `tests/monitoring/` | ✅ Consistente |
| V08 | `structlog` em todos os logs — PLAN menciona `logger.info/warning` com eventos estruturados | ✅ Consistente |

---

## Fase 1 — Dia 1 (Settings + priceProtect + max_position_pct)

### Task-001: Expandir Settings com campos SPEC_043

**Design Pattern:** **Builder** — Settings é construído incrementalmente através de múltiplas SPECs (029 → 030 → 043)

- **Arquivos:** `src/config/settings.py`, `.env.example`
- **Risco:** 🟢 Baixo (risco zero — novos campos com defaults seguros)
- **Estimativa:** 15 min
- **Depende de:** Nada

**Definition of Done:**
- [ ] Campos adicionados em `Settings`:
  ```python
  max_position_pct: Annotated[float, Field(ge=0, le=100)] = 0.0
  consecutive_loss_threshold: Annotated[int, Field(ge=1, le=10)] = 3
  portfolio_loss_threshold: Annotated[int, Field(ge=1, le=10)] = 2
  slippage_tolerance_multiplier: Annotated[float, Field(ge=1.0, le=2.0)] = 1.10
  slippage_tolerance_reduced: Annotated[float, Field(ge=1.0, le=1.5)] = 1.05
  cb_risk_reduction_factor: Annotated[float, Field(ge=0.1, le=1.0)] = 0.5
  portfolio_risk_reduction_factor: Annotated[float, Field(ge=0.1, le=1.0)] = 0.75
  slippage_validation_enabled: bool = True
  circuit_breaker_enabled: bool = True
  ```
- [ ] `price_protect_enabled` **NÃO** criado (INV-043-01)
- [ ] `python -c "from src.config.settings import Settings, get_settings; get_settings.cache_clear(); s=get_settings(); assert s.slippage_tolerance_multiplier==1.10"` passa
- [ ] `.env.example` atualizado com seção `# ─── SPEC_043 Slippage Protection ───`
- [ ] `ruff check src/config/settings.py` limpo

---

### Task-002: priceProtect em STOP_MARKET e TAKE_PROFIT_MARKET

**Design Pattern:** **Decorator** — Adiciona comportamento de proteção (`priceProtect`) às ordens existentes sem modificar a lógica de criação de ordens. O Decorator compõe-se com o parâmetro `reduceOnly` existente.

- **Arquivos:** `src/exchange/binance_client.py` — métodos `create_stop_loss_order()`, `create_take_profit_order()`
- **Risco:** 🟢 Baixo (adição de flag em params)
- **Estimativa:** 30 min (inclui try/except fallback — ver V01)
- **Depende de:** Nada

**Definition of Done:**
- [ ] `create_stop_loss_order()` envolve criação em try/except:
  ```python
  params = {"stopPrice": stop_price, "reduceOnly": True, "priceProtect": True}
  try:
      order = await self._exchange.create_order(...)
  except ccxt.BadRequest:
      params.pop("priceProtect", None)
      order = await self._exchange.create_order(...)
      logger.warning("priceProtect_fallback_stop_loss", symbol=symbol)
  ```
- [ ] `create_take_profit_order()` mesmo padrão com try/except
- [ ] `except ccxt.BadRequest` (não `Exception`) conforme PRD D02 e resolução V01
- [ ] Log WARN estruturado emitido no fallback
- [ ] `ruff check src/exchange/binance_client.py` limpo

---

### Task-003: priceProtect condicional em trailing stop com fallback

**Design Pattern:** **Decorator** com **failover** — Tenta com priceProtect; se `ccxt.BadRequest`, remove e reenvia sem. O Decorator envolve a chamada original com tentativa e fallback.

- **Arquivos:** `src/exchange/binance_client.py` — método `create_trailing_stop_order()`
- **Risco:** 🟡 Médio (TRAILING_STOP_MARKET via Algo Orders API pode não suportar priceProtect)
- **Estimativa:** 15 min
- **Depende de:** Task-002 (priceProtect em SL/TP)

**Definition of Done:**
- [ ] `create_trailing_stop_order()` com try/except:
  ```python
  try:
      params["priceProtect"] = True
      order = await self._exchange.create_order(...)
  except ccxt.BadRequest:
      params.pop("priceProtect", None)
      order = await self._exchange.create_order(...)
      logger.warning("priceProtect_not_supported_for_trailing_stop", symbol=symbol)
  ```
- [ ] Exceção NÃO `BadRequest` propaga (não engolida)
- [ ] `ruff check src/exchange/binance_client.py` limpo

---

### Task-004: Implementar max_position_pct no RiskManager

**Design Pattern:** **Decorator** — Adiciona restrição percentual sobre o clamp existente sem modificar a fórmula de position sizing. O clamp original (`min(max_position_usdt, ...)`) é decorado com `effective_max = min(max_position_usdt, balance * pct/100)`.

- **Arquivos:** `src/trading/risk_manager.py`
  - `__init__()`: novo parâmetro `max_position_pct: float = 0.0`
  - `_calculate_atr()`: modificar clamp
  - `calculate()`: passar `available_balance` para `_calculate_atr()`
- **Risco:** 🟡 Médio (mudança de assinatura em `calculate()` — verificar quem chama)
- **Estimativa:** 15 min
- **Depende de:** Task-001 (settings)

**Definition of Done:**
- [ ] Construtor aceita `max_position_pct: float = 0.0`
- [ ] Se `max_position_pct > 0`: `effective_max = min(self._max_position_usdt, balance * pct / 100)`
- [ ] Se `max_position_pct == 0`: usa `self._max_position_usdt` (comportamento legado)
- [ ] `calculate()` passa `available_balance` como argumento nomeado para `_calculate_atr()`
- [ ] `ruff check src/trading/risk_manager.py` limpo

---

### Task-005: Testes priceProtect

**Design Pattern:** **Test Double** — Mocks da exchange para verificar params sem chamar API real

- **Arquivos:** `tests/exchange/test_binance_client.py` (criar ou estender)
- **Estimativa:** 30 min
- **Depende de:** Task-002, Task-003

**Fixtures:**
- `_mock_exchange_assert_params()` — `AsyncMock` para `create_order` que inspeciona `params` e asserta `params["priceProtect"] is True`
- `_ccxt_bad_request_mock()` — levanta `ccxt.BadRequest` na 1ª chamada, succeed na 2ª

**Definition of Done:**
- [ ] TEST-043-01: `create_stop_loss_order()` → `params["priceProtect"] == True` com exchange mockada
- [ ] TEST-043-02: `create_take_profit_order()` → `params["priceProtect"] == True`
- [ ] TEST-043-17: Trailing stop + `ccxt.BadRequest` → fallback sem priceProtect + log WARN
- [ ] TEST-043-17b: Trailing stop + `ccxt.AuthenticationError` → propaga (não engolida)
- [ ] `pytest tests/exchange/test_binance_client.py -v` com 3 testes passando

---

## Fase 2 — Dia 3-5 (Slippage Model + Validação)

### Task-006: Extrair `_compute_atr_value()` como Facade

**Design Pattern:** **Facade** — Fornece uma interface simplificada para obter o valor ATR atual, escondendo a complexidade do cálculo interno. Tanto `_calculate_atr()` quanto `calculate()` podem usar esse método.

- **Arquivos:** `src/trading/risk_manager.py`
- **Risco:** 🟡 Médio (refatoração — precisa garantir que `_calculate_atr()` retorna mesmos valores)
- **Estimativa:** 15 min
- **Depende de:** Nada (independe de Settings)

**Definition of Done:**
- [ ] Método `_compute_atr_value(self, df: pd.DataFrame) -> float` criado
- [ ] `_calculate_atr()` usa `_compute_atr_value()` internamente (refatorado, sem duplicação)
- [ ] Retorna `0.0` se df vazio ou None
- [ ] Teste de regressão: `_calculate_atr()` com dados conhecidos retorna mesmo valor de antes da refatoração
- [ ] `ruff check src/trading/risk_manager.py` limpo

---

### Task-007: Implementar `_estimate_slippage()`

**Design Pattern:** **Strategy** — O tier de liquidez (high/medium/low) seleciona a estratégia de slippage estático. O componente dinâmico (ATR% × 0.5) é aditivo, com `max()` selecionando o pior caso entre as duas estratégias.

- **Arquivos:** `src/trading/risk_manager.py`
- **Risco:** 🟡 Médio (divisão por zero se `entry_price=0`)
- **Estimativa:** 30 min
- **Depende de:** Task-006 (precisa de `atr_value`), Task-001 (settings com tiers)

**Definition of Done:**
- [ ] Método `_estimate_slippage(symbol, quantity, entry_price, atr_value) -> float`
- [ ] `static_slippage = liq_tier_pct * notional` (tier do `backtest_slippage_liq_map.get(symbol, "medium")`)
- [ ] `dynamic_slippage = (atr_value / entry_price) * notional * 0.5` se atr_value e entry_price > 0
- [ ] Retorna `max(static, dynamic)` com proteção contra divisão por zero
- [ ] Log estruturado: `logger.info("slippage_estimated", symbol=..., tier=..., slippage_usdt=..., atr_ratio=...)`
- [ ] `ruff check src/trading/risk_manager.py` limpo

---

### Task-008: Gate de slippage em `_calculate_atr()`

**Design Pattern:** **Chain of Responsibility** — Gate é um elo na cadeia de validação em `calculate()`: `[intraday_loss → stop_distance → zero → slippage → actual_risk]`. Cada gate decide passar ou rejeitar.

- **Arquivos:** `src/trading/risk_manager.py` (`_calculate_atr()`)
- **Risco:** 🟡 Médio (falso positivo — rejeitar trades válidos)
- **Estimativa:** 30 min
- **Depende de:** Task-007, Task-004 (para signature de `_calculate_atr()`)

**Definition of Done:**
- [ ] Após `actual_risk_usdt = qty * effective_stop` e `actual_risk_usdt > max_risk_usdt` (INV-029-05):
  ```python
  if self._slippage_validation_enabled:
      slippage_est = self._estimate_slippage(symbol, qty, entry_price, atr_value)
      total_risk = actual_risk_usdt + slippage_est
      tolerance = self._slippage_tolerance_reduced if self._circuit_breaker_active else self._slippage_tolerance_multiplier
      if total_risk > self._risk_per_trade_usdt * tolerance:
          self._set_rejection(code="SLIPPAGE_EXCEEDS_TOLERANCE", ...)
          return None
      logger.info("slippage_check_passed", symbol=..., total_risk=..., tolerance=...)
  ```
- [ ] Gate só executa se `self._slippage_validation_enabled == True`
- [ ] Tolerância reduzida (D07): `1.05` se `circuit_breaker_active`, senão `1.10`
- [ ] `ruff check src/trading/risk_manager.py` limpo

---

### Task-009: Gate de slippage em `_calculate_fixed()`

**Design Pattern:** **Chain of Responsibility** — Mesma cadeia, método de position sizing diferente

- **Arquivos:** `src/trading/risk_manager.py` (`_calculate_fixed()`)
- **Risco:** 🟡 Médio (`_calculate_fixed()` não expõe `actual_risk_usdt` — usar `risk_amount` como proxy)
- **Estimativa:** 15 min
- **Depende de:** Task-008

**Definition of Done:**
- [ ] Após `qty = round(raw_qty, precision)` e antes do return:
  ```python
  if self._slippage_validation_enabled:
      actual_risk_usdt = qty * stop_distance  # ou reusa risk_amount
      slippage_est = self._estimate_slippage(symbol, qty, entry_price, atr_value=0)  # só estático
      total_risk = actual_risk_usdt + slippage_est
      tolerance = self._slippage_tolerance_reduced if self._circuit_breaker_active else self._slippage_tolerance_multiplier
      if total_risk > self._risk_per_trade_usdt * tolerance:
          self._set_rejection(code="SLIPPAGE_EXCEEDS_TOLERANCE", ...)
          return None
  ```
- [ ] Chama `_estimate_slippage(atr_value=0)` — apenas componente estático (modo FIXED não tem ATR)
- [ ] `ruff check src/trading/risk_manager.py` limpo

---

### Task-010: Testes slippage + max_position_pct

- **Arquivos:** `tests/trading/test_risk_manager.py`
- **Fixtures:** `_risk_manager_with_slippage()` — RiskManager com `_liq_map` e `_slippage_map` injetados
- **Estimativa:** 45 min
- **Depende de:** Task-004, Task-007, Task-008, Task-009

**Definition of Done:**
- [ ] TEST-043-03: Slippage BTCUSDT (tier "high"=0.03%) → valor calculado estático ≥ 0.03% do notional
- [ ] TEST-043-04: Slippage CHZUSDT (desconhecido → fallback "medium" 0.08%) → 0.08% do notional
- [ ] TEST-043-05: Risco+slip > 1.10× → `None` + `_last_rejection.code == "SLIPPAGE_EXCEEDS_TOLERANCE"`
- [ ] TEST-043-06: Risco+slip ≤ 1.10× → `PositionSize` válido
- [ ] TEST-043-10: `max_position_pct=50` com balance=300 → posição limitada a $150
- [ ] TEST-043-11: `max_position_pct=0` → posição usa `MAX_POSITION_USDT` ($500)
- [ ] `pytest tests/trading/test_risk_manager.py -v` com 6 testes passando

---

## Fase 3 — Semana 2 (Circuit Breaker + Wiring)

### Task-011: Implementar `register_trade_outcome()` com State Pattern

**Design Pattern:** **State** — O circuit breaker opera em 3 estados:
- `NORMAL` (sem perdas consecutivas, risco cheio)
- `ACTIVE` (threshold atingido, risco reduzido por `cb_risk_reduction_factor`)
- `RECOVERY` (acumulando vitórias para reset)

Cada transição é determinada pelo valor de `pnl_usdt` e pelo estado atual.

- **Arquivos:** `src/trading/risk_manager.py`
  - `__init__()`: novo parâmetros + `_cb_lock = asyncio.Lock()`
  - Novo método `async def register_trade_outcome(self, pnl_usdt: float) -> None`
  - Propriedade `effective_risk_per_trade_usdt` (reflete valor reduzido quando CB ativo)
  - `import asyncio` adicionado ao topo do arquivo
- **Risco:** 🔴 Alto (race condition com múltiplos trades — ver D09)
- **Estimativa:** 45 min
- **Depende de:** Task-001 (settings), resolução V01-V04

**Definition of Done:**
- [ ] `asyncio.Lock` protegendo estado (`self._cb_lock`)
- [ ] Zona morta: `if abs(pnl_usdt) <= 0.001: return` (D10)
- [ ] Perda (`pnl_usdt < -0.001`): incrementa `_consecutive_losses`, reseta `_recovery_wins_count`
- [ ] Se `_consecutive_losses >= threshold`: ativa CB, `_risk_per_trade_usdt = max(original * factor, 1.0)`
- [ ] Vitória (`pnl_usdt > 0.001`): se CB ativo, incrementa `_recovery_wins_count`; se `>= recovery_wins_needed`, reseta completamente
- [ ] Se CB inativo: reseta `_consecutive_losses = 0`
- [ ] `effective_risk_per_trade_usdt` property retorna valor atual
- [ ] `logger.warning("circuit_breaker_activated", ...)` e `logger.info("circuit_breaker_reset", ...)`
- [ ] Só executa se `self._circuit_breaker_enabled == True`
- [ ] `ruff check src/trading/risk_manager.py` limpo

---

### Task-012: Criar TradeCloseRouter (Mediator Pattern)

**Design Pattern:** **Mediator** — O Mediator (TradeCloseRouter) centraliza a comunicação entre OrderMonitor (que não conhece RiskManager) e os RiskManagers por par + portfolio CB. Em vez de OrderMonitor saber de N RiskManagers, ele só conhece o Mediator.

```
OrderMonitor ──▶ TradeCloseRouter (Mediator) ──▶ RiskManager[parA]
                                      ├──▶ RiskManager[parB]
                                      └──▶ Portfolio CB (self)
```

- **Arquivos:** `src/trading/trade_close_router.py` (NOVO)
- **Risco:** 🔴 Alto (acoplamento — router precisa referenciar RiskManager sem criar import cíclico)
- **Estimativa:** 30 min
- **Depende de:** Task-011

**Definition of Done:**
- [ ] `class TradeCloseRouter`:
  ```python
  class TradeCloseRouter:
      def __init__(self, portfolio_threshold=2, portfolio_reduction=0.75):
          self._rms: dict[str, RiskManager] = {}
          self._portfolio_losses: int = 0
          self._portfolio_breaker_active: bool = False
          self._portfolio_lock = asyncio.Lock()
          ...
      
      def register(self, symbol: str, rm: RiskManager) -> None: ...
      
      async def __call__(self, symbol: str, pnl_usdt: float) -> None:
          rm = self._rms.get(symbol)
          if rm:
              await rm.register_trade_outcome(pnl_usdt)
          await self._update_portfolio(pnl_usdt)
  ```
- [ ] Portfolio CB: threshold=2, reduction=0.75 (PRD D04), mesma zona morta D10
- [ ] `asyncio.Lock` no portfolio state
- [ ] `ruff check src/trading/trade_close_router.py` limpo

---

### Task-013: Adicionar callback `on_trade_closed` no OrderMonitor

**Design Pattern:** **Observer** — OrderMonitor é o Subject que emite eventos `trade_closed`. O callback registrado (Router) é o Observer. O Subject não conhece o Observer concreto, apenas o contrato `Callable`.

- **Arquivos:** `src/monitoring/order_monitor.py`
  - `__init__()`: novo parâmetro `on_trade_closed: Callable[[str, float], Awaitable[None]] | None = None`
  - `_handle_tp_executed()`: chamar callback APÓS `update_trade_status`
  - `_handle_sl_executed()`: idem
  - `_handle_manual_close()`: idem
- **Risco:** 🔴 Alto (callback chamado antes de persistir trade → estado inconsistente se callback falhar)
- **Estimativa:** 30 min
- **Depende de:** Task-012

**Definition of Done:**
- [ ] Tipo do callback: `Callable[[str, float], Awaitable[None]]` (async — ver V02)
- [ ] Nos 3 handlers (`tp_executed`, `sl_executed`, `manual_close`), chamar APÓS `update_trade_status()` e `audit()`:
  ```python
  if self._on_trade_closed:
      await self._on_trade_closed(symbol, pnl_usdt)
  ```
- [ ] Se callback falha (exception), logar WARN mas NÃO impedir fechamento do trade
- [ ] `ruff check src/monitoring/order_monitor.py` limpo

---

### Task-014: Wiring no `_main()` com mapeamento de rejection codes

**Design Pattern:** **Builder** — Orquestra a construção do grafo de dependências: define a ordem correta de inicialização (Settings → Router → RMs → OrderMonitor → TradingMonitors) e injeta as dependências.

- **Arquivos:** `src/main.py`
  - `_main()`: criar `TradeCloseRouter`, registrar no `OrderMonitor` e em `_build_monitor()`
  - `_build_monitor()`: registrar cada RiskManager no router
  - `_map_risk_rejection_outcome()`: adicionar novos códigos
- **Risco:** 🔴 Alto (ordem de inicialização — router criado antes dos monitores)
- **Estimativa:** 30 min
- **Depende de:** Task-013, Task-012, Task-008, Task-009

**Definition of Done:**
- [ ] `_main()` cria `TradeCloseRouter` ANTES de `RuntimeMonitorRegistry`
- [ ] `_build_monitor()` registra cada RM no router: `router.register(cfg.symbol, risk_manager)`
- [ ] `OrderMonitor` recebe `on_trade_closed=router`
- [ ] `_map_risk_rejection_outcome()` mapeia:
  ```python
  "SLIPPAGE_EXCEEDS_TOLERANCE": "REJECTED_RISK_SLIPPAGE",
  "CIRCUIT_BREAKER_ACTIVE": "REJECTED_RISK_CIRCUIT_BREAKER",
  ```
- [ ] Ordem de inicialização: `Settings → Router → RiskManagers → OrderMonitor → TradingMonitors`
- [ ] `ruff check src/main.py` limpo

---

### Task-015: Testes circuit breaker pair-level

- **Arquivos:** `tests/trading/test_risk_manager.py`
- **Fixtures:** `_risk_manager_with_cb(**overrides)`, `_concurrent_trades_coro(rm, n=3)`
- **Estimativa:** 60 min
- **Depende de:** Task-011

**Definition of Done:**
- [ ] TEST-043-07: `register_trade_outcome(-5.0)` × 3 → `circuit_breaker_active == True`
- [ ] TEST-043-08: CB ativo → `register_trade_outcome(+3.0)` × 1 → reset completo (contador=0, breaker=False)
- [ ] TEST-043-09: `register_trade_outcome(-5.0)` × 1 → ainda `circuit_breaker_active == False`
- [ ] TEST-043-12: `cb_risk_reduction_factor=0.1` com `risk_per_trade_usdt=5.0` → effective=1.0 (piso $1.00)
- [ ] TEST-043-13: `register_trade_outcome(0.0005)` → zona morta, não altera contadores
- [ ] TEST-043-14: 3 chamadas simultâneas com `asyncio.gather` → estado final consistente (lock)
- [ ] TEST-043-16: Criar nova instância → `consecutive_losses=0`, `circuit_breaker_active=False`
- [ ] `pytest tests/trading/test_risk_manager.py -v` com 7 testes passando

---

### Task-016: Testes integração (callback + fuzzing + INT)

- **Arquivos:**
  - `tests/monitoring/test_order_monitor.py` (callback)
  - `tests/trading/test_risk_manager.py` (fuzzing)
- **Fixtures:** `_mock_callback()` — AsyncMock que captura `(symbol, pnl_usdt)`
- **Estimativa:** 30 min
- **Depende de:** Task-013, Task-014

**Definition of Done:**
- [ ] TEST-043-15: `OrderMonitor(on_trade_closed=_mock_callback)` → TP executado → callback chamado com `(symbol, pnl_usdt)`
- [ ] TEST-043-18: Fuzzing: 100 cenários com `_risk_manager_with_slippage()` + `_risk_manager_with_cb()` — validar que INV-029-05 nunca é violado (actual_risk_usdt ≤ 1.05× config) mesmo com slippage ativo
- [ ] INT-043-01: priceProtect na resposta Testnet (skippable se geobloqueado — documentar fallback)
- [ ] INT-043-02: CB + slippage + sizing em tick completo via `SimulatedBinanceClient` (se viável em CI)
- [ ] `pytest tests/monitoring/test_order_monitor.py tests/trading/test_risk_manager.py -v`

---

## Fase 4 — Verificação Final

### Task-017: Ruff + Cobertura + Cross-reference

- **Arquivos:** Todos modificados + `docs/SDD/SPEC.md`
- **Estimativa:** 15 min
- **Depende de:** Todas as anteriores

**Definition of Done:**
- [ ] `ruff check src/ tests/` limpo
- [ ] `ruff format src/ tests/` sem alterações
- [ ] `pytest tests/ -v --tb=short` com todos os 18+ testes passando
- [ ] `pytest --cov=src --cov-fail-under=80` passa (gate CI)
- [ ] Cross-reference: `docs/SDD/SPEC.md` § Referências adicionada entrada `SPEC_043 — Slippage Protection e Circuit Breaker`

---

## Someday (Pós-MVP)

### Task-018: R5 — ATR_MULTIPLIER_OVERRIDES default para low-cap

- **Arquivos:** `.env.example`, `.env`
- **Estimativa:** 15 min
- **Status:** ✅ Concluído
- **Nota:** Inicialmente post-MVP (PRD §3.3), movido para MVP por decisão do Time B. Defaults low-cap adicionados ao `.env.example` com documentação. `.env` atualizado com merge dos overrides XAUUSDT + low-cap pairs.

---

## Dependências Entre Tasks

```
Task-001 (Settings)
 ├──► Task-002 (priceProtect SL/TP) ──► Task-003 (priceProtect trailing) ──► Task-005 (Testes priceProtect)
 ├──► Task-004 (max_position_pct) ──► Task-010 (Testes slippage+max)
 ├──► Task-006 (compute_atr_value) ──► Task-007 (_estimate_slippage) ──► Task-008 (Gate ATR) ──► Task-009 (Gate Fixed) ──► Task-010
 └──► Task-011 (CB register_trade_outcome) ──► Task-012 (TradeCloseRouter) ──► Task-013 (OrderMonitor callback) ──► Task-014 (Wiring main) ──► Task-015+016 (Testes CB+INT)
                                                                                                                        └──► Task-017 (Lint+cobertura)

Task-018 (R5 post-MVP) — independente
```

---

## Mapa de Padrões de Design

| Task | Padrão | Papel |
|------|--------|-------|
| 001 | **Builder** | Settings construído incrementalmente por SPECs |
| 002 | **Decorator** | priceProtect decora ordem sem modificar criação |
| 003 | **Decorator** | priceProtect + failover em trailing stop |
| 004 | **Decorator** | Clamp percentual decora clamp absoluto |
| 006 | **Facade** | `_compute_atr_value()` simplifica acesso ao ATR |
| 007 | **Strategy** | Tier de liquidez seleciona estratégia de slippage |
| 008-009 | **Chain of Responsibility** | Gates em sequência decidem rejeitar ou passar |
| 011 | **State** | CB: NORMAL → ACTIVE → RECOVERY |
| 012 | **Mediator** | Router centraliza comunicação OM ↔ RMs |
| 013 | **Observer** | OrderMonitor emite eventos, Router consome |
| 014 | **Builder** | Orquestra grafo de dependências no startup |
| 005+010+015+016 | **Test Double** | Mocks, stubs e fakes para isolamento |

---

## Resumo

| Fase | Tasks | Padrões | Rollout | Esforço |
|------|-------|---------|---------|---------|
| Dia 1 | 001-005 | Builder, Decorator, Test Double | Imediato | ~2h |
| Dia 3-5 | 006-010 | Facade, Strategy, Chain of Responsibility | Feature flag | ~2.5h |
| Semana 2 | 011-016 | State, Mediator, Observer, Builder, Test Double | Feature flag | ~3.5h |
| Final | 017 | — | Imediato | ~15min |
| Post-MVP | 018 | — | Futuro | ~15min |
| **Total** | **18 tasks** | **7 padrões** | **3 PRs** | **~8h** |
