# SPEC_043 — Slippage Protection, priceProtect e Circuit Breaker de Perdas

**ID:** SPEC_043
**Status:** Rascunho
**Data:** 2026-05-12
**Versão:** 2.0
**Dependências:** SPEC_029 (Position Sizing por ATR), SPEC_006 (Métricas de Performance)
**Skill de validação:** `sdd-spec-driven-development`, `qa-review`, `security-audit`

---

## 1. Título e Resumo

### 1.1 Nome da Funcionalidade

Camada de proteção contra slippage na execução de stops + circuit breaker de perdas consecutivas

### 1.2 Resumo

**O que é:** Conjunto de 3 mecanismos de segurança que atuam em conjunto para conter perdas reais dentro do risco configurado por trade:

1. **priceProtect** nas ordens STOP_MARKET e TAKE_PROFIT_MARKET — troca trigger de last price para mark price, eliminando stops falsos por wicks.
2. **Modelo de slippage na validação de risco** — usa os tiers de liquidez já definidos (`backtest_slippage_by_liq`) para estimar o pior caso de slippage e bloquear trades cujo risco real (risco teórico + slippage estimada) exceda 1.10× o `RISK_PER_TRADE_USDT`.
3. **Circuit breaker de perdas consecutivas** — reduz progressivamente o `RISK_PER_TRADE_USDT` após N perdas consecutivas, com reset após vitória.

**Por que estamos fazendo:** Análise forense de 10 trades reais mostrou que, embora o win rate seja de 70%, o PnL líquido é negativo (−$5,98) porque a perda média (−$8,35) é 3,1× maior que o lucro médio (+$2,72). O outlier CHZUSDT (−$16,42) perdeu 3,28× o risco configurado de $5,00 — diferença de $11,42 atribuída a slippage na execução do stop loss em par de baixa liquidez.

**Valor de negócio:** Elimina o principal fator de erosão de capital — perdas que extrapolam o risco configurado — mantendo a assimetria positiva esperada da estratégia (win rate elevado) sem o downside de slippage descontrolada.

**Conexão com PRD/SPEC:** Complementa SPEC_029 (§ Risco Real INV-029-05), estendendo a validação de risco teórico para incluir slippage estimada. Atende ao princípio "Risk-first: nenhuma posição abre sem stop-loss já enviado" do AGENTS.md, adicionando "e sem validação de slippage".

---

## 2. Objetivos e Escopo

### 2.1 Objetivos

- [ ] R1: Adicionar `priceProtect: True` em todas as ordens STOP_MARKET e TAKE_PROFIT_MARKET (`src/exchange/binance_client.py`)
- [ ] R2: Implementar estimativa de slippage por par no `RiskManager.calculate()` usando os tiers `backtest_slippage_by_liq` + `backtest_slippage_liq_map`
- [ ] R3: Rejeitar trade se `(risco_teórico + slippage_estimada) > RISK_PER_TRADE_USDT × 1.10`
- [ ] R4: Implementar circuit breaker de perdas consecutivas no `RiskManager`
- [ ] R6: Migrar `MAX_POSITION_USDT` de valor absoluto para `max_position_as_pct_of_balance` com fallback para o valor absoluto existente

### 2.2 Fora do Escopo

- **Não inclui:** Implementação de trailing stop (já existe via SPEC_030 V2)
- **Não inclui:** Implementação de TP parcial (já existe via SPEC_030)
- **Não inclui:** Implementação de novas exchanges
- **Não inclui:** Implementação de Kelly Criterion (será avaliada em SPEC futura)
- **Não inclui:** Validação de correlação entre posições abertas simultâneas
- **Não inclui:** Validação de distância mínima SL-entry (pode virar SPEC_044)

### 2.3 Futuro / Post-MVP

- [x] R5: Configurar `ATR_MULTIPLIER_OVERRIDES` default para pares de baixo preço/liquidez no `.env`

> **Nota:** Adiado para post-MVP — disponível como config manual opcional.
> `ATR_MULTIPLIER_OVERRIDES` continua funcionando via `.env` como config opcional, mas não é requisito obrigatório desta SPEC.

---

## 3. Referências

| Documento | Seção | Relevância |
|---|---|---|
| `docs/SDD/SPEC.md` | § 2.4 Exchange Integration | Contrato de ordens STOP_MARKET/TAKE_PROFIT_MARKET |
| `docs/SDD/SPEC_029/SPEC.md` | § 6 INV-029-05 | Risco real ≤ 1.05× configurado |
| `docs/SDD/SPEC_029/SPEC.md` | § 4 Fórmula ATR | Position sizing atual |
| `docs/SDD/SPEC_044_PREDICTIVE_CIRCUIT_BREAKER/SPEC.md` | — | Circuit breaker preditivo (follow-up SPEC_043) |
| `src/exchange/binance_client.py` | `create_stop_loss_order()`, `create_take_profit_order()` | Onde priceProtect será adicionado |
| `src/trading/risk_manager.py` | `_calculate_atr()`, `calculate()` | Onde slippage model e circuit breaker serão inseridos |
| `src/config/settings.py` | `backtest_slippage_by_liq`, `backtest_slippage_liq_map` | Tiers de liquidez existentes (reutilizados) |
| `src/config/settings.py` | `risk_per_trade_usdt` | Valor que o circuit breaker reduzirá |
| `REPORT_ANALISE_RISCO_2026-05-12` | — | Análise forense que originou esta SPEC |

---

## 4. Histórias de Usuário e Requisitos

### US-043-01: priceProtect em ordens STOP_MARKET e TAKE_PROFIT_MARKET

> Como **operador**, quero **que os stops sejam acionados pelo mark price (preço justo) em vez do last price (último negócio)** para **evitar que wicks momentâneos no livro de ofertas disparem stops falsos e causem perdas desnecessárias**.

**Critérios de Aceitação:**

```text
DADO   uma ordem STOP_MARKET sendo criada para um símbolo
QUANDO o parâmetro params é montado em create_stop_loss_order()
ENTÃO  params inclui "priceProtect": True
```

```text
DADO   uma ordem TAKE_PROFIT_MARKET sendo criada para um símbolo
QUANDO o parâmetro params é montado em create_take_profit_order()
ENTÃO  params inclui "priceProtect": True
```

- [ ] AC-01: `create_stop_loss_order()` envia `"priceProtect": True` no params
- [ ] AC-02: `create_take_profit_order()` envia `"priceProtect": True` no params
- [ ] AC-03: Testnet mostra ordens com trigger por mark price (campo `priceProtect` na resposta da API)
- [ ] AC-04: Sem mudança de comportamento se `priceProtect` não for suportado pela exchange (default False)

### US-043-02: Modelo de slippage na validação de risco

> Como **gestor de risco**, quero **que o RiskManager estime o custo de slippage de cada par antes de aprovar o trade** para **que uma perda real nunca ultrapasse um limite seguro mesmo em condições adversas de liquidez**.

**Critérios de Aceitação:**

```text
DADO   um sinal sendo avaliado pelo RiskManager.calculate()
QUANDO o par está mapeado em backtest_slippage_liq_map
ENTÃO  a slippage estimada é calculada como: slippage_pct * entry_price * quantity
       E o risco total (risco_teórico + slippage_estimada) é validado contra RISK_PER_TRADE_USDT * 1.10
```

```text
DADO   um par NÃO mapeado em backtest_slippage_liq_map
QUANDO o RiskManager avalia o trade
ENTÃO  usa o tier "medium" (slippage 0.08%) como default seguro
```

- [ ] AC-01: Se `risco_teórico + slippage_estimada > RISK_PER_TRADE_USDT * 1.10`, retorna `None` com `RiskRejection(code="SLIPPAGE_EXCEEDS_TOLERANCE")`
- [ ] AC-02: Se o par não está no `backtest_slippage_liq_map`, usa "medium" (0.08%)
- [ ] AC-03: Log estruturado inclui `slippage_estimate_usdt`, `slippage_tier`, `total_risk_usdt`
- [ ] AC-04: Parâmetro de tolerância `slippage_tolerance_multiplier: float = 1.10` configurável no construtor do RiskManager

### US-043-03: Circuit breaker de perdas consecutivas

> Como **operador**, quero **que o sistema reduza automaticamente o risco após uma sequência de perdas** para **preservar capital durante drawdowns e evitar que losses acumulados agravem o impacto**.

**Critérios de Aceitação:**

```text
DADO   uma sequência de N perdas consecutivas registradas
QUANDO N >= CONSECUTIVE_LOSS_THRESHOLD (default: 3)
ENTÃO  risk_per_trade_usdt é reduzido para risk_per_trade_usdt * LOSS_REDUCTION_FACTOR (default: 0.5)
```

```text
DADO   o circuit breaker está ativo (risk_per_trade_usdt reduzido)
QUANDO ocorre uma vitória (trade com PnL > 0)
ENTÃO  o contador de perdas consecutivas é zerado
       E risk_per_trade_usdt retorna ao valor original configurado
```

- [ ] AC-01: `CONSECUTIVE_LOSS_THRESHOLD` default = 3 (configurável, interval [1, 10])
- [ ] AC-02: `LOSS_REDUCTION_FACTOR` default = 0.5 (configurável, interval (0, 1])
- [ ] AC-03: `RECOVERY_WINS_NEEDED` default = 1 (configurável, ≥ 1) — número de vitórias consecutivas para reset completo
- [ ] AC-04: Contador persiste na instância do RiskManager (por processo). Em reinicialização do bot, o contador é resetado.
- [ ] AC-05: Log estruturado em cada ativação/reset: `circuit_breaker_activated`, `circuit_breaker_reset`
- [ ] AC-06: RiskRejection code específico: `code="CIRCUIT_BREAKER_ACTIVE"` se o breaker estiver ativo (opcional, para dashboard)

### US-043-04: ATR_MULTIPLIER_OVERRIDES default para pares de baixa liquidez

> Como **operador**, quero **que pares de baixo preço unitário e baixa liquidez recebam um ATR_MULTIPLIER maior por default** para **reduzir o position size e, consequentemente, o impacto absoluto da slippage nesses pares**.

**Critérios de Aceitação:**

```text
DADO   o arquivo .env com ATR_MULTIPLIER_OVERRIDES configurado
QUANDO o RiskManager calcula position size para um par listado
ENTÃO  usa o multiplier específico do par em vez do global
```

- [x] AC-01: `.env` atualizado com `ATR_MULTIPLIER_OVERRIDES={"XAUUSDT":3.0,"CHZUSDT":4.0,"GMTUSDT":4.0,"FIDAUSDT":3.5,"PHAUSDT":3.5,"JSTUSDT":3.0,"JUPUSDT":3.0}`
- [x] AC-02: Valores documentados no `.env.example` como defaults recomendados para low-cap
- [ ] AC-03: Validado em testnet que position size é efetivamente menor com multiplier maior

### US-043-05: MAX_POSITION como percentual do saldo

> Como **gestor de risco**, quero **que o limite máximo de posição por trade seja calculado como percentual do saldo disponível** para **escalar automaticamente com o crescimento (ou encolhimento) da conta**.

**Critérios de Aceitação:**

```text
DADO   o RiskManager com max_position_pct configurado (default: 50%)
QUANDO o position size calculado excede max_position_pct do saldo
ENTÃO  o position size é limitado a max_position_pct do saldo
       E um log de warning é emitido
```

- [ ] AC-01: Novo campo `max_position_pct: float = 50.0` (0 < pct <= 100) no Settings e no RiskManager
- [ ] AC-02: `max_position_usdt_effective = min(settings.max_position_usdt, balance * max_position_pct / 100)`
- [ ] AC-03: Se `max_position_pct` for 0, desabilitado (usa apenas `MAX_POSITION_USDT` absoluto)

---

## 5. Design e Arquitetura

### 5.1 priceProtect — Mudança em `src/exchange/binance_client.py`

**Before (atual):**
```python
async def create_stop_loss_order(self, symbol, side, quantity, stop_price):
    params = {
        "stopPrice": stop_price,
        "reduceOnly": True,
    }
    order = await self._exchange.create_order(
        symbol=symbol, type="STOP_MARKET",
        side=side, amount=quantity, params=params,
    )
```

**After:**
```python
async def create_stop_loss_order(self, symbol, side, quantity, stop_price):
    params = {
        "stopPrice": stop_price,
        "reduceOnly": True,
        "priceProtect": True,  # SPEC_043: mark price trigger
    }
    order = await self._exchange.create_order(
        symbol=symbol, type="STOP_MARKET",
        side=side, amount=quantity, params=params,
    )
```

Mesma mudança em `create_take_profit_order()`.

**Trailing stop com priceProtect (fallback):**
```python
# priceProtect é suportado apenas em STOP_MARKET e TAKE_PROFIT_MARKET.
# TRAILING_STOP_MARKET usa a Algo Orders API que pode não suportar o parâmetro.
# Tentativa com fallback silencioso:

async def create_trailing_stop_order(self, ...):
    params = {
        "trailingPercent": callback_rate,
        "trailingTriggerPrice": activation_price,
        "reduceOnly": True,
    }
    try:
        # Tentar com priceProtect
        params["priceProtect"] = True
        order = await self._exchange.create_order(
            symbol=symbol, type="TRAILING_STOP_MARKET",
            side=side, amount=quantity, params=params,
        )
    except Exception:
        # Fallback: remover priceProtect e reenviar
        params.pop("priceProtect", None)
        order = await self._exchange.create_order(
            symbol=symbol, type="TRAILING_STOP_MARKET",
            side=side, amount=quantity, params=params,
        )
        logger.warning("priceProtect_not_supported_for_trailing_stop", symbol=symbol)
    return order
```

### 5.2 Modelo de Slippage — `src/trading/risk_manager.py`

**Novo método em RiskManager:**
```python
def _estimate_slippage(
    self,
    symbol: str,
    quantity: float,
    entry_price: float,
    atr_value: float,  # SPEC_043 V2: ATR para slippage dinâmico
) -> float:
    """Estima slippage em USDT para o par dado.

    Usa os tiers de liquidez definidos em backtest_slippage_by_liq
    e o mapeamento em backtest_slippage_liq_map.

    Se o par não está mapeado, usa default "medium" (0.08%).
    """
    # Determinar tier de liquidez
    liquidy_map = getattr(self, '_liq_map', {})
    tier = liquidy_map.get(symbol, "medium")

    # Obter slippage percentual para o tier
    slippage_map = getattr(self, '_slippage_map', {})
    slippage_pct = slippage_map.get(tier, 0.0008)

    notional = entry_price * quantity
    static_slippage = slippage_pct * notional

    # Slippage dinâmica: 50% do ATR% aplicado ao nocional
    atr_ratio = atr_value / entry_price if atr_value and entry_price > 0 else 0
    dynamic_slippage = atr_ratio * notional * 0.5

    slippage_usdt = max(static_slippage, dynamic_slippage)
    return slippage_usdt
```

> **Nota:** Requer acesso ao ATR value — passado por parâmetro de `_calculate_atr()` onde `atr_value` já está disponível.

**Modificação em `calculate()`:**
```python
# Após o cálculo de position size, antes de retornar:
slippage_estimate = self._estimate_slippage(
    symbol=signal.symbol,
    quantity=qty,
    entry_price=signal.entry_price,
    atr_value=atr_value,  # vindo de _calculate_atr()
)

total_risk = actual_risk_usdt + slippage_estimate
max_allowed_risk = self._risk_per_trade_usdt * self._slippage_tolerance_multiplier

if total_risk > max_allowed_risk:
    self._set_rejection(
        code="SLIPPAGE_EXCEEDS_TOLERANCE",
        reason="slippage_estimate_exceeds_tolerance",
        details={
            "actual_risk_usdt": round(actual_risk_usdt, 4),
            "slippage_estimate_usdt": round(slippage_estimate, 4),
            "total_risk_usdt": round(total_risk, 4),
            "max_allowed_risk_usdt": round(max_allowed_risk, 4),
            "slippage_tier": tier,
            "slippage_pct": slippage_pct,
        },
    )
    return None

# Log estruturado
logger.info(
    "slippage_check_passed",
    symbol=signal.symbol,
    actual_risk_usdt=round(actual_risk_usdt, 4),
    slippage_estimate_usdt=round(slippage_estimate, 4),
    total_risk_usdt=round(total_risk, 4),
    max_allowed_risk_usdt=round(max_allowed_risk, 4),
    slippage_tier=tier,
)
```

**Nota:** A validação INV-029-05 existente (risco ≤ 1.05×) permanece. O slippage check é uma validação ADICIONAL, não substituta.

### 5.3 Circuit Breaker — `src/trading/risk_manager.py`

**Novos atributos no construtor do RiskManager:**
```python
# SPEC_043 — Circuit Breaker
self._consecutive_losses: int = 0
self._consecutive_loss_threshold: int = kwargs.get("consecutive_loss_threshold", 3)
self._loss_reduction_factor: float = kwargs.get("loss_reduction_factor", 0.5)
self._recovery_wins_needed: int = kwargs.get("recovery_wins_needed", 1)
self._recovery_wins_count: int = 0
self._original_risk_per_trade_usdt: float = risk_per_trade_usdt
self._circuit_breaker_active: bool = False
```

**Novos métodos:**
```python
def register_trade_outcome(self, pnl_usdt: float) -> None:
    """Registra resultado de trade para o circuit breaker.

    Deve ser chamado pelo TradingMonitor após o fechamento de cada trade.
    """
    if pnl_usdt > 0:
        # Vitória
        if self._circuit_breaker_active:
            self._recovery_wins_count += 1
            if self._recovery_wins_count >= self._recovery_wins_needed:
                # Reset completo
                self._circuit_breaker_active = False
                self._consecutive_losses = 0
                self._recovery_wins_count = 0
                self._risk_per_trade_usdt = self._original_risk_per_trade_usdt
                logger.info(
                    "circuit_breaker_reset",
                    reason="recovery_wins_achieved",
                    recovery_wins_needed=self._recovery_wins_needed,
                    restored_risk_usdt=self._risk_per_trade_usdt,
                )
        else:
            self._consecutive_losses = 0
    else:
        # Perda
        self._consecutive_losses += 1
        self._recovery_wins_count = 0
        if (self._consecutive_losses >= self._consecutive_loss_threshold
                and not self._circuit_breaker_active):
            self._circuit_breaker_active = True
            reduced_risk = self._original_risk_per_trade_usdt * self._loss_reduction_factor
            self._risk_per_trade_usdt = max(reduced_risk, 1.0)  # piso de $1
            logger.warning(
                "circuit_breaker_activated",
                consecutive_losses=self._consecutive_losses,
                threshold=self._consecutive_loss_threshold,
                original_risk_usdt=self._original_risk_per_trade_usdt,
                reduced_risk_usdt=self._risk_per_trade_usdt,
                reduction_factor=self._loss_reduction_factor,
            )


@property
def circuit_breaker_active(self) -> bool:
    return self._circuit_breaker_active

@property
def effective_risk_per_trade_usdt(self) -> float:
    """Retorna o risk_per_trade_usdt ativo (pode estar reduzido pelo circuit breaker)."""
    return self._risk_per_trade_usdt
```

**Integração no TradingMonitor** (`src/main.py` ou `src/trading/monitor.py`):
```python
# Após fechamento de trade (SL ou TP executado):
if trade.pnl_usdt is not None:
    risk_manager.register_trade_outcome(trade.pnl_usdt)
```

### 5.3.1 Circuit Breaker de Portfólio (adicional)

```python
# Portfolio-level circuit breaker (MainRiskManager)
# Compartilhado entre todos os pares. Ativa quando N losses consecutivos
# ocorrem EM QUALQUER PAR (perda global).
self._portfolio_consecutive_losses: int = 0
self._portfolio_loss_threshold: int = kwargs.get("portfolio_loss_threshold", 4)
self._portfolio_risk_reduction_factor: float = kwargs.get("portfolio_risk_reduction_factor", 0.5)
self._portfolio_breaker_active: bool = False
```

```python
def register_portfolio_trade_outcome(self, pnl_usdt: float) -> None:
    """Registra resultado no circuit breaker de portfólio.

    Chamado pelo TradingMonitor central (não por par).
    Quando ativo, aplica redução adicional sobre TODOS os pares.
    """
    # Lógica similar ao pair-level, mas com threshold=4 default
    # e redução afeta o risk_per_trade_usdt global
```

> **Nota:** O circuit breaker de portfólio é uma camada adicional. Ambos operam independentemente.

### 5.4 MAX_POSITION como % do saldo — `src/trading/risk_manager.py`

**Modificação no clamp do ATR mode (`_calculate_atr`):**
```python
# Calcular max_position_usdt dinâmico
max_by_pct = available_balance * self._max_position_pct / 100.0
effective_max_position = min(self._max_position_usdt, max_by_pct)

position_usdt = self._risk_per_trade_usdt * signal.entry_price / effective_stop
position_usdt = max(
    self._min_position_usdt,
    min(position_usdt, effective_max_position),
)
```

**Novo campo no construtor:**
```python
self._max_position_pct: float = kwargs.get("max_position_pct", 50.0)
```

### 5.5 Arquivos Afetados

| Arquivo | Mudança |
|---|---|
| `src/exchange/binance_client.py` | Adicionar `priceProtect: True` em SL e TP |
| `src/trading/risk_manager.py` | Novo método `_estimate_slippage()`, validação no `calculate()`, circuit breaker com `register_trade_outcome()`, `max_position_pct` |
| `src/config/settings.py` | Novos campos: `consecutive_loss_threshold`, `loss_reduction_factor`, `recovery_wins_needed`, `max_position_pct`, `slippage_tolerance_multiplier` |
| `src/main.py` (ou monitor) | Chamar `register_trade_outcome()` ao fechar trade |
| `.env` / `.env.example` | Adicionar `ATR_MULTIPLIER_OVERRIDES` para low-cap + novos campos |
| `docs/SDD/SPEC.md` | § 2.2 Risk Manager — atualizar contratos |

---

## 6. Regras de Negócio e Restrições

### 6.1 Invariantes

| ID | Invariante | Violação → Ação |
|---|---|---|
| INV-043-01 | `priceProtect` nunca deve ser falseável por configuração externa | Fixo em `True` no código, sem variável de ambiente |
| INV-043-02 | Slippage estimada nunca deve reduzir position size abaixo de `MIN_POSITION_USDT` | Slippage é verificada APÓS o sizing, não durante |
| INV-043-03 | Circuit breaker nunca reduz risco abaixo de $1.00 USDT | Piso hardcoded `max(reduced_risk, 1.0)` |
| INV-043-04 | `max_position_pct` nunca permite posição maior que `MAX_POSITION_USDT` absoluto | `effective_max = min(pct_of_balance, absolute_max)` |
| INV-043-05 | `register_trade_outcome()` só aceita PnL de trades FECHADOS | Deve ser chamado apenas com `trade.pnl_usdt is not None` |
| INV-043-06 | Circuit breaker reseta após reinicialização do bot | Contador não é persistido em MongoDB (intencional: após restart, começa limpo) |

### 6.2 Validações Obrigatórias

- `slippage_pct >= 0` antes de usar no cálculo
- `consecutive_loss_threshold >= 1` — se 0, circuit breaker desabilitado
- `loss_reduction_factor > 0` e `<= 1.0` — se 0, risco vai a zero (inconsistent)
- `recovery_wins_needed >= 1`
- `max_position_pct` no intervalo (0, 100] — se 0, desabilitado

### 6.3 Limitações Técnicas

- `priceProtect`: Binance Futures suporta `priceProtect` para STOP_MARKET e TAKE_PROFIT_MARKET em todos os pares USDT-M. Confirmar na doc: Binance suporta desde 2022.
- CCXT: O parâmetro `priceProtect` é passado diretamente no `params` dict. CCXT não faz validação — é passado como está para a API.
- Slippage estimada é um modelo — não substitui a execução real. Serve como gate de segurança.
- Circuit breaker não é persistido: em restart do bot, o contador de perdas é zerado. Isso é intencional (evita "carregar" drawdown entre sessões).

### 6.4 Padrões de Segurança

- `priceProtect` não expõe informações sensíveis (é apenas flag na ordem)
- Logs de circuit breaker nunca incluem API keys
- `_estimate_slippage` usa dados do settings, não de input externo

---

## 7. Testes e Validação

### 7.1 Testes Unitários

| ID | Descrição | Cenário | Prioridade |
|---|---|---|---|
| TEST-043-01 | priceProtect está presente nas ordens SL | `create_stop_loss_order` chamado → params contém `priceProtect: True` | Alta |
| TEST-043-02 | priceProtect está presente nas ordens TP | `create_take_profit_order` chamado → params contém `priceProtect: True` | Alta |
| TEST-043-03 | Slippage estimada para par conhecido | Par "BTCUSDT" no tier "high" → slippage_pct = 0.03% | Alta |
| TEST-043-04 | Slippage estimada para par desconhecido | Par "CHZUSDT" não mapeado → fallback "medium" = 0.08% | Alta |
| TEST-043-05 | Trade rejeitado se slippage + risco excede tolerância | `risco+slip > 1.10 × $5` → `None` com código `SLIPPAGE_EXCEEDS_TOLERANCE` | Alta |
| TEST-043-06 | Trade aprovado se slippage + risco dentro da tolerância | `risco+slip <= 1.10 × $5` → `PositionSize` válido | Alta |
| TEST-043-07 | Circuit breaker ativa após N perdas consecutivas | `register_trade_outcome(-loss)` × 3 → `circuit_breaker_active = True` | Alta |
| TEST-043-08 | Circuit breaker reseta após vitórias suficientes | Ativo → `register_trade_outcome(+profit)` × 1 → reset completo | Alta |
| TEST-043-09 | Circuit breaker não ativa sem perdas suficientes | `register_trade_outcome(-loss)` × 1 → `circuit_breaker_active = False` | Média |
| TEST-043-10 | max_position_pct limita posição | `balance=300`, `max_position_pct=50` → `effective_max=150 < 500` | Alta |
| TEST-043-11 | max_position_pct=0 desabilita | `balance=300`, `max_position_pct=0` → usa `MAX_POSITION_USDT=500` | Média |
| TEST-043-12 | Circuit breaker piso de $1.00 | `risk=5.0`, `factor=0.1` → `reduced=0.5` → `effective=1.0` (piso) | Média |

### 7.2 Testes de Integração (Testnet)

| ID | Descrição | Pré-requisito |
|---|---|---|
| INT-043-01 | priceProtect aparece na resposta da ordem na Testnet | Credenciais Testnet, par com liquidez |
| INT-043-02 | Circuit breaker + slippage + position sizing funcionam juntos em um tick completo | Testnet ativa, RiskManager configurado |

### 7.3 Evidências Requeridas na PR

- [ ] Output de `pytest tests/ -v --tb=short` com todas as asserções passando
- [ ] Log de 1 ciclo no Testnet mostrando `slippage_check_passed` ou `slippage_exceeds_tolerance`
- [ ] Log de `circuit_breaker_activated` após alimentar perdas consecutivas no teste
- [ ] Referência cruzada: SPEC_043 → SPEC_029 (INV-029-05) → código

---

## 8. Tratamento de Erros

| Erro / Condição | Causa | Ação do Sistema |
|---|---|---|
| Slippage estimada + risco excede tolerância | Par de baixa liquidez com position size grande | Rejeitar trade com `RiskRejection(code="SLIPPAGE_EXCEEDS_TOLERANCE")` |
| Circuit breaker ativo | Perdas consecutivas >= threshold | Reduzir `risk_per_trade_usdt` para `original × factor` |
| `priceProtect` rejeitado pela exchange | Exchange não suporta o parâmetro (versão antiga) | Fallback silencioso: remover `priceProtect` e reenviar. Log WARN. |
| `max_position_pct` = 0 | Desabilitado intencionalmente pelo operador | Usa apenas `MAX_POSITION_USDT` existente |
| `max_position_pct` resulta em valor < `MIN_POSITION_USDT` | Saldo muito pequeno para o % configurado | Usar `MIN_POSITION_USDT` como piso. Log WARN. |

---

## 9. Riscos e Mitigações

| Risco | Impacto | Mitigação |
|---|---|---|
| priceProtect muda comportamento de triggers e pode afetar estratégias que dependem de last price | Médio | BO Williams usa fractais de 5 barras (estruturais), não scalping. Mark price é mais alinhado com a estratégia. |
| Slippage estimada pode ser imprecisa para pares sem histórico de liquidez | Médio | Tiers são conservadores (high=0.03%, medium=0.08%, low=0.15%). Em caso de dúvida, usar "low". |
| Circuit breaker pode ser acionado por perdas normais em sequência (volatilidade) | Baixo | Threshold default = 3 permite 2 perdas isoladas. Redução de 50% ainda permite operar, só reduz exposição. |
| Portfolio circuit breaker pode reduzir risco de todos os pares simultaneamente após 4 losses | Médio | Threshold=4 para portfólio vs 3 para par. Redução de 50% ainda permite operar. |
| Circuit breaker não persistido entre restart pode perder proteção | Baixo | Intencional: restart limpa estado. Em produção normal, bot não reinicia com frequência. |

---

## 10. Definição de Pronto (DoD Global)

- [ ] R1: `priceProtect: True` adicionado em todas as ordens STOP_MARKET e TAKE_PROFIT_MARKET
- [ ] R2: `_estimate_slippage()` implementado no RiskManager
- [ ] R3: Validação de slippage no `calculate()` com rejeição documentada
- [ ] R4: `register_trade_outcome()` + lógica de circuit breaker implementados
- [ ] R6: `max_position_pct` implementado como limite adicional ao `MAX_POSITION_USDT`
- [ ] R7: Settings expandido com novos campos
- [ ] R8: TEST-043-01 a TEST-043-12 passando no `pytest`
- [ ] R9: `ruff check src/ tests/` limpo
- [ ] R10: Logs estruturados de slippage_check e circuit_breaker presentes

### Post-MVP (vazio — R5 movido para MVP)

Nenhum requisito pendente pós-MVP.

---

## 11. Plano de Entrega

1. **Planner Agent** transforma a SPEC em Task Graph com dependências:
   - Task 1: priceProtect (R1) — sem dependências
   - Task 2: ATR_MULTIPLIER_OVERRIDES (R5) — sem dependências
   - Task 3: max_position_pct (R6) — dependente de Settings expandido
   - Task 4: Modelo de slippage (R2, R3) — dependente de Settings expandido
   - Task 5: Circuit breaker (R4) — dependente de Settings expandido
   - Task 6: Testes (R8) — dependente de todas as tasks anteriores
   - Task 7: Atualização SPEC.md (nova seção 2.2) — após implementação
2. **Dev Agent** executa o Task Graph na ordem definida
3. **Validation Agent** valida conformidade (SPEC → testes → comportamento)
4. **Commit / Review Gate** — libera PR após parecer de validação

---

## Histórico

- **2026-05-12:** Criação da SPEC_043 — baseada em análise forense de 10 trades reais; identificou slippage descontrolada como causa primária de erosão de capital.
