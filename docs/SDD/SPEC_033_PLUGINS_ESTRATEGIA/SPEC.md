# SPEC_033 — Arquitetura de Plugins de Estratégia

**ID:** SPEC_033
**Título:** Arquitetura de Plugins de Estratégia
**Data:** 2026-05-13
**Status:** Implementado (Code Review pendente)
**Versão:** 1.5
**Dependências:** SPEC_013 (validação signal engine), SPEC_032 (observabilidade)
**PRD §:** Fase 2 — "Framework de estratégias plugáveis"
**Refinado por:** Time A (@trader-senior, @product-owner, @risk-manager, @quant-developer, @ml-engineer)
**Pareceres consultados:** @backend-senior, @trader-senior, @risk-manager, @quant-developer
**Code Review:** @optimization-review — Análise de otimização aplicada em 2026-05-13

---

## 1. Objetivo

Substituir o acoplamento rígido entre `SignalEngine` e a lógica BO Williams por uma arquitetura de plugins que permita carregar, testar e alternar entre múltiplas estratégias sem modificar o core do bot.

O `SignalEngine` atual eval hardcoded da estratégia Phicube. Além disso, uma única instância de `SignalEngine` é **compartilhada entre todos os `TradingMonitor`** — o campo mutável `_last_evaluation` pode ser sobrescrito por chamadas concorrentes de símbolos diferentes, corrompendo o audit trail de avaliação de sinais (raça crítica identificada em code review de otimização).

Com plugins, o operador pode:
- Rodar estratégias diferentes por símbolo
- A/B testar estratégias em paralelo
- Adicionar nova estratégia sem reiniciar o container
- **Cada `TradingMonitor` ter sua própria instância de `SignalEngine`**, eliminando a condição de corrida

---

## 2. Escopo

### Dentro do escopo
- Interface abstrata `StrategyPlugin` com métodos `evaluate()`, `name`, `warmup_candles()`
- Dataclass `SignalResult` com campos obrigatórios de entrada/saída
- Implementação da estratégia Phicube como plugin concreto (`WilliamsStrategy`)
- Loader dinâmico que descobre plugins via `importlib.metadata.entry_points`
- `PluginProxy` com timeout (`asyncio.wait_for`) para isolamento de falhas
- Chain of Responsibility: plugin configurado → WilliamsStrategy (fallback imutável)
- Config `SYMBOL_STRATEGY_MAP` mapeando símbolo → plugin name
- `DEFAULT_STRATEGY` para símbolos não mapeados
- Testes com plugin mock e plugin lento

### Fora do escopo
- Hot-reload de plugins sem restart (será SPEC futura)
- Marketplace de estratégias
- Interface visual para seleção de estratégia
- Meta-estratégia (ensemble/voting) — possível extensão futura

---

## 3. User Stories

### US-033-01 — Plugin carregado por config
**Como** operador,
**quero** configurar `SYMBOL_STRATEGY_MAP = {"BTCUSDT": "williams", "ETHUSDT": "williams"}`,
**para** que cada símbolo use a estratégia desejada.

**Critério de aceite:**
- `SignalEngine` carrega plugin correto por símbolo
- Se símbolo não mapeado, usa `DEFAULT_STRATEGY`

### US-033-02 — Nova estratégia = novo arquivo
**Como** desenvolvedor,
**quero** criar `src/strategies/macd_strategy.py` implementando `StrategyPlugin`,
**para** adicionar estratégia sem modificar SignalEngine.

**Critério de aceite:**
- Plugin descoberto automaticamente ao instalar o pacote (entry_points)
- `evaluate()` chamado com mesmos parâmetros que a engine atual

### US-033-03 — Regra Mestre (Williams sempre disponível)
**Como** operador,
**quero** que a estratégia BO Williams esteja **sempre** disponível como fallback,
**para** que o bot nunca pare de operar mesmo que o plugin configurado falhe.

**Critério de aceite:**
- WilliamsStrategy carregado na inicialização antes de qualquer outro plugin
- WilliamsStrategy não pode ser sobrescrito por colisão de nome
- Se plugin configurado retorna None ou lança exceção → Chain cai no Williams

---

## 4. Design Patterns Aplicados

A arquitetura usa 3 padrões de design validados pelo Time A (com suporte da skill `design-patterns`), mais 5 padrões complementares identificados em análise de alinhamento com o código existente do projeto.

### 4.1 Proxy Pattern — `PluginProxy`

**Problema:** Um plugin pode travar (loop infinito, rede lenta) e bloquear o event loop do asyncio inteiro.

**Solução:** Cada plugin real é envolvido por um `PluginProxy` que controla o acesso:

```
SignalEngine → PluginProxy → asyncio.wait_for() → Plugin.evaluate()
```

- Proxy implementa `StrategyPlugin` (mesma interface)
- Adiciona `asyncio.wait_for(evaluate(), timeout=plugin_timeout)` (default 30s)
- Captura `TimeoutError` e `Exception`, loga falha estruturada, retorna `None`
- Permite timeouts diferentes por plugin sem modificar o plugin real

### 4.2 Chain of Responsibility — Regra Mestre

**Problema:** Garantir que o bot nunca fique sem estratégia mesmo que o plugin configurado falhe.

**Solução:** Cadeia de 2 handles em ordem fixa:

1. **Handle Primário** — plugin do `SYMBOL_STRATEGY_MAP` (dinâmico)
2. **Handle Fallback** — `WilliamsStrategy` (sempre carregado, imutável)

```
SignalEngine.evaluate(symbol, df)
  ├── 1. Tenta plugin_configurado(symbol) → se retorna Signal → OK
  │         ↓ (None ou exceção)
  └── 2. Tenta WilliamsStrategy → se retorna Signal → OK
              ↓ (None)
         Retorna None (nenhuma estratégia viu oportunidade)
```

**Regra Mestre:**
- `WilliamsStrategy` ocupa slot protegido `plugins["williams"]`
- Nenhum outro plugin pode sobrescrever este slot (loga erro se tentar)
- Se `DEFAULT_STRATEGY = "williams"` e símbolo não mapeado → Handle 1 já é o Williams
- Se `DEFAULT_STRATEGY ≠ "williams"` e símbolo não mapeado → Handle 1 tenta a default, Handle 2 é Williams

### 4.3 Strategy Pattern — Confidence por Plugin

**Problema:** Confidence score de 0.0 a 1.0 é genérico demais — cada estratégia calcula de forma diferente.

**Solução:** Cada plugin define seu próprio cálculo de confidence internamente. O valor é exposto via `metadata["confidence"]`, não como campo raiz do `SignalResult`. O RiskManager pode optar por usar ou ignorar.

Para o `WilliamsStrategy`, a fórmula será:

```python
def _calculate_confidence(self, df, direction, fractal_ref) -> float:
    ao_magnitude = abs(ao[-1]) / atr[-1]          # 0.0 a 0.5
    ao_divergence = _count_recent_crosses(ao, 3)   # 0.0 a 0.3
    fractal_dist = abs(close - fractal_ref) / atr   # 0.0 a 0.2
    return min(1.0, ao_magnitude + ao_divergence + fractal_dist)
```

### 4.4 Multi-Instance Pattern — SignalEngine por Monitor

**Problema (descoberto em code review de otimização):** O `SignalEngine` atual é instanciado uma única vez em `main.py:743` e injetado como singleton no `RuntimeMonitorRegistry`. Todos os `TradingMonitor` compartilham a mesma instância. `evaluate()` modifica `_last_evaluation` (line 123) sem lock — chamadas concorrentes de diferentes símbolos corrompem o estado.

**Solução:** Cada `TradingMonitor` cria sua própria instância de `SignalEngine` (que por sua vez carrega seu próprio conjunto de plugins):

```
RuntimeMonitorRegistry._build_monitor()
  └── TradingMonitor(
        signal_engine=SignalEngine(risk_reward_ratio=X),
        ...
      )
```

**Benefícios:**
- Elimina condição de corrida em `_last_evaluation`
- Isola plugins por monitor (cada um pode ter um conjunto diferente)
- Simplifica testes unitários (cada monitor é independente)
- Nenhum lock adicional necessário no hot path

**Implementação na migração:**
```python
# ANTES (main.py:743 — compartilhado):
signal_engine = SignalEngine(risk_reward_ratio=settings.risk_reward_ratio)
monitor_registry = RuntimeMonitorRegistry(
    signal_engine=signal_engine,  # mesma instância para todos
    ...
)

# DEPOIS (main.py — cada monitor cria o seu):
# signal_engine removido de RuntimeMonitorRegistry.__init__
# _build_monitor cria internamente:
def _build_monitor(self, cfg, router):
    return TradingMonitor(
        signal_engine=SignalEngine(risk_reward_ratio=self._settings.risk_reward_ratio),
        ...
    )
```

---

### 4.5 Registry Pattern — `PluginRegistry`

**Problema:** `SignalEngine._load_plugins()` atualmente acumula 3 responsabilidades: (1) descoberta via entry_points, (2) wrapping com Proxy, (3) validação da Regra Mestre. Violação de SRP. Dificulta testar descoberta sem avaliar sinais.

**Solução:** Extrair um `PluginRegistry` que gerencia o ciclo de vida dos plugins:

```
PluginRegistry
  ├── discover()           → entry_points → lista de plugins raw
  ├── register(plugin)     → valida, wrappa com Proxy, insere no dict
  ├── validate_master()    → WilliamsStrategy sempre presente
  ├── get_plugin(name)     → retorna PluginProxy
  └── health_check()       → verifica se todos os plugins respondem
```

```python
class PluginRegistry:
    """Gerencia descoberta, registro e ciclo de vida de plugins."""

    def __init__(self, group: str = "phicube.strategies", timeout: float = 30.0):
        self._group = group
        self._timeout = timeout
        self._plugins: dict[str, PluginProxy] = {}

    def discover(self) -> list[type[StrategyPlugin]]:
        """Retorna classes de plugin via importlib.metadata.entry_points."""
        ...

    def register(self, plugin: StrategyPlugin) -> None:
        """Valida, wrappa com Proxy e registra."""
        if plugin.name == "williams":
            logger.warning("cannot_override_williams")
            return
        if plugin.name in self._plugins:
            logger.warning("plugin_already_registered", name=plugin.name)
            return
        self._plugins[plugin.name] = PluginProxy(plugin, timeout=self._timeout)

    def validate_master(self) -> None:
        """Regra Mestre: WilliamsStrategy sempre carregado."""
        ...

    def health_check(self) -> dict[str, bool]:
        """Retorna status de cada plugin: {name: True/False}."""
        ...
```

**Benefícios:**
- `SignalEngine` foca apenas em avaliação (Chain of Responsibility)
- `PluginRegistry` testável independentemente
- Adicionar health check (futuro) sem modificar SignalEngine
- Alinha com `SLMissingState` / `ManualClosePendingState` — estado de lifecycle já é padrão no projeto

**Alinhamento com o projeto:** O `OrderMonitor` já gerencia estados de lifecycle de trades (`_sl_missing_state`, `_manual_close_pending`). O `PluginRegistry` segue o mesmo padrão de gestão de estado separada da lógica de negócio.

---

### 4.6 Null Object Pattern — `NullSignalResult`

**Problema:** `SignalEngine.evaluate()` retorna `SignalResult | None`. Cada handle na Chain precisa verificar `if result is not None:` — ruído que esconde a intenção. O operador `None` tem significado ambíguo: "plugin falhou" vs "plugin não viu oportunidade" vs "tempo esgotado".

**Solução:** Substituir `None` por `NullSignalResult` — objeto que implementa `SignalResult` com `direction=None` e é falsy no contexto da chain:

```python
@dataclass
class NullSignalResult(SignalResult):
    direction: None = None
    entry_price: None = None
    stop_loss: None = None
    take_profit: None = None
    metadata: dict = field(default_factory=lambda: {"reason": "no_signal"})

    def __bool__(self) -> bool:
        return False  # Falsy para simplificar chain
```

**Chain simplificada:**
```python
async def evaluate(self, symbol, timeframe, df) -> SignalResult:
    result = await self._plugins[plugin_name].evaluate(symbol, timeframe, df)
    if result:      # NullSignalResult é falsy
        return result
    result = await self._plugins["williams"].evaluate(symbol, timeframe, df)
    if result:
        return result
    return NullSignalResult(reason="no_plugin_generated_signal")
```

**Benefícios:**
- Elimina `is not None` checks
- `reason` em metadata permite diferenciar "timeout", "exception", "no_opportunity"
- Compatível com `INV-033-01` (nunca lança exceção)
- Alinha com princípios de programação funcional (Monad / Maybe)

---

### 4.7 Decorator Pattern — Capabilidades Plugáveis

**Problema:** Atualmente, `PluginProxy` adiciona apenas timeout. Outras capabilidades transversais (validação de SL/TP, logging, metrics, rate limiting) precisariam ser adicionadas dentro do Proxy ou duplicadas em cada plugin.

**Solução:** Cadeia de decorators em torno do plugin real, onde cada decorator implementa `StrategyPlugin` e adiciona uma capability:

```python
# Decorator base
class PluginDecorator(StrategyPlugin):
    def __init__(self, wrapped: StrategyPlugin):
        self._wrapped = wrapped

    @property
    def name(self) -> str:
        return self._wrapped.name

    async def evaluate(self, symbol, timeframe, df) -> SignalResult:
        return await self._wrapped.evaluate(symbol, timeframe, df)

    def warmup_candles(self) -> int:
        return self._wrapped.warmup_candles()

# Decorators concretos
class TimeoutDecorator(PluginDecorator):
    def __init__(self, wrapped: StrategyPlugin, timeout: float = 30.0):
        super().__init__(wrapped)
        self._timeout = timeout

    async def evaluate(self, symbol, timeframe, df) -> SignalResult:
        try:
            return await asyncio.wait_for(
                self._wrapped.evaluate(symbol, timeframe, df),
                timeout=self._timeout,
            )
        except TimeoutError:
            return NullSignalResult(reason=f"timeout_{self._timeout}s")

class MetricsDecorator(PluginDecorator):
    async def evaluate(self, symbol, timeframe, df) -> SignalResult:
        result = await self._wrapped.evaluate(symbol, timeframe, df)
        record_signal_evaluated(symbol, timeframe)
        if result:
            record_signal_detected(symbol, timeframe, result.direction.lower())
        return result
```

**Composição:**
```python
plugin = MetricsDecorator(
    TimeoutDecorator(
        ValidationDecorator(  # valida SL/TP bounds
            WilliamsStrategy(),
            max_sl_pct=10.0,
        ),
        timeout=30.0,
    ),
)
```

**Benefícios:**
- Cada decorator tem responsabilidade única (SRP)
- Plugins reais não precisam saber de timeout, metrics, validação
- Ordem dos decorators é configurável
- Reutilizável entre plugins diferentes

**Alinhamento com o projeto:** O `_create_order_with_protect` em `binance_client.py` já usa **Template Method** para adicionar priceProtect com fallback — mesmo princípio de camadas de comportamento em torno de uma operação core.

---

### 4.8 Template Method Pattern — Ciclo de Avaliação do Plugin

**Problema:** Cada plugin implementa `evaluate()` livremente. Não há garantia de que o fluxo (indicadores → condições → SL/TP → confiança) seja seguido consistentemente. Isso pode levar a plugins que esquecem de validar SL ou calcular confidence.

**Solução:** A classe base `StrategyPlugin` fornece um **Template Method** `evaluate()` que define o esqueleto do algoritmo, deixando etapas específicas para subclasses:

```python
class StrategyPlugin(ABC):
    """Template Method: evaluate() define o esqueleto; subclasses implementam ganchos."""

    async def evaluate(self, symbol: str, timeframe: str, df: pd.DataFrame) -> SignalResult:
        """Template Method — não sobrescrever. Subclasses sobrescrevem os ganchos."""
        validated_df = await self._validate_input(df)
        enriched = await self._compute_indicators(validated_df)
        direction = await self._check_conditions(enriched)
        if direction is None:
            return NullSignalResult(reason=f"{self.name}_no_opportunity")
        sl, tp = await self._calculate_targets(enriched, direction)
        confidence = await self._calculate_confidence(enriched, direction)
        return self._build_result(direction, sl, tp, confidence, enriched)

    # ── Ganchos para subclasses ─────────────────────────────────
    async def _validate_input(self, df: pd.DataFrame) -> pd.DataFrame:
        """Valida tamanho mínimo, colunas necessárias. Padrão: len >= warmup."""
        if len(df) < self.warmup_candles():
            raise ValueError(f"need at least {self.warmup_candles()} candles")
        return df

    @abstractmethod
    async def _compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula indicadores específicos da estratégia."""

    @abstractmethod
    async def _check_conditions(self, enriched: pd.DataFrame) -> str | None:
        """Retorna 'LONG', 'SHORT', ou None."""

    @abstractmethod
    async def _calculate_targets(
        self, enriched: pd.DataFrame, direction: str
    ) -> tuple[float, float]:
        """Retorna (stop_loss, take_profit)."""

    async def _calculate_confidence(self, enriched: pd.DataFrame, direction: str) -> float:
        """Padrão: 1.0. Subclasses podem sobrescrever."""
        return 1.0

    def _build_result(self, direction, sl, tp, confidence, enriched) -> SignalResult:
        """Monta SignalResult com metadata."""
        return SignalResult(
            direction=direction,
            entry_price=float(enriched.iloc[-1]["close"]),
            stop_loss=sl,
            take_profit=tp,
            metadata={"confidence": confidence, "plugin": self.name},
        )
```

**Benefícios:**
- Consistência entre plugins — todos seguem o mesmo fluxo
- Subclasses só precisam implementar `_compute_indicators`, `_check_conditions`, `_calculate_targets`
- Template garante que SL/TP sempre são calculados
- Confidence tem default 1.0 (plugins simples não precisam implementar)

**Alinhamento com o projeto:** O mesmo padrão já existe em `binance_client._create_order_with_protect()` que define o esqueleto (tenta com priceProtect → fallback sem) e delega detalhes para métodos específicos (`create_stop_loss_order`, `create_take_profit_order`).

---

### 4.9 Observer Pattern — Eventos de Sinal

**Problema:** Atualmente, métricas (`record_signal_detected`), notificações e persistência são chamadas diretamente dentro de SignalEngine/TradingMonitor. Cada novo consumidor de sinal exige modificar o fluxo de avaliação.

**Solução:** `SignalEngine` emite eventos após cada avaliação. Componentes interessados (Metrics, Notifier, Repository, RiskManager) se inscrevem como observers:

```python
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

class SignalEvent(StrEnum):
    EVALUATED = "signal_evaluated"
    DETECTED = "signal_detected"
    REJECTED = "signal_rejected"

@dataclass
class SignalEventData:
    event: SignalEvent
    symbol: str
    timeframe: str
    result: SignalResult | NullSignalResult
    duration_ms: float = 0.0

# Opção A: EventEmitter interno ao SignalEngine
class SignalEngine:
    def __init__(self, ...):
        self._listeners: dict[SignalEvent, list[Callable]] = {}

    def on(self, event: SignalEvent, callback: Callable) -> None:
        self._listeners.setdefault(event, []).append(callback)

    def _emit(self, event: SignalEvent, data: SignalEventData) -> None:
        for cb in self._listeners.get(event, []):
            try:
                cb(data)
            except Exception:
                logger.exception("listener_failed", event=event.value)

    async def evaluate(self, symbol, timeframe, df) -> SignalResult:
        start = time.time()
        result = await self._chain_evaluate(symbol, timeframe, df)
        duration_ms = (time.time() - start) * 1000
        event = SignalEvent.DETECTED if result else SignalEvent.EVALUATED
        self._emit(event, SignalEventData(event, symbol, timeframe, result, duration_ms))
        return result
```

**Uso no TradingMonitor:**
```python
# Em vez de chamar record_signal_* manualmente:
engine.on(SignalEvent.DETECTED, lambda d: record_signal_detected(d.symbol, d.timeframe, ...))
engine.on(SignalEvent.EVALUATED, lambda d: record_signal_evaluated(d.symbol, d.timeframe))
```

**Benefícios:**
- Desacopla produtores de sinais de consumidores
- Novo consumidor = novo `engine.on(...)` — sem modificar SignalEngine
- Compatível com os decorators (MetricsDecorator pode virar um observer)
- Eventos podem ser logados no audit trail do MongoDB

**Alinhamento com o projeto:** O sistema de notificações do bot já usa padrão similar: `NotificationEvent` enum + `Notifier.send(event, data)`. O Observer proposto estende esse conceito para dentro do SignalEngine.

---

### 4.10 Mapa de Padrões — Projeto vs SPEC_033

| Padrão | Força | Onde existe no projeto | Onde se aplica na SPEC_033 |
|--------|-------|----------------------|---------------------------|
| **Template Method** | 100% | `_create_order_with_protect()` em binance_client.py — esqueleto fixo com fallback, 3 callers (stop, TP, trailing) | `StrategyPlugin.evaluate()` — esqueleto com 5 ganchos: validate → compute → check → targets → confidence. Mesmo padrão. |
| **Observer / Event** | 100% | `NotificationEvent` (StrEnum) + `Notifier.send(event, payload)`. `common/events.py` tem 3 eventos adicionais. | `SignalEngine.on(SignalEvent, callback)` + `_emit()` — eventos EVALUATED, DETECTED, REJECTED. Mesmo contrato. |
| **Chain of Responsibility** | 100% | — (novo na SPEC_033) | Handle 1: plugin configurado → Handle 2: Williams fallback. **Genuinamente novo.** |
| **Null Object** | 100% | — (novo na SPEC_033). Sentinel `_NO_FALLBACK` em `common/decorators.py` é similar em espírito, mas não Null Object. | `NullSignalResult` — falsy em `__bool__`, carrega `reason` na metadata. **Genuinamente novo.** |
| **Factory Method** | 85% | `PanelFactory.create_stat_panel()` (static method retornando dict) | `PluginRegistry.register()` cria instância + aplica decorators. Conceito igual, mecanismo diferente (objeto vs dict). |
| **Strategy (enum/tipos)** | 70% | `ExitStrategy(StrEnum)` + `SizingMode(StrEnum)` com `if/elif` switches em OrderManager/RiskManager | `SignalResult.metadata["confidence"]` — cada plugin define seu cálculo internamente. Alinhamento conceitual (cada variação decide como calcular), não estrutural (enum vs metadata). |
| **Decorator** | 70% | `@safe_async`, `@retry` em `common/decorators.py` — **decorators de função Python** (wrapper em torno de callable). | `PluginDecorator`, `TimeoutDecorator` — **Decorator de classe GoF** (delegação via composição). Ambos válidos, mas estruturalmente diferentes. A cadeia de decorators da SPEC_033 pode usar a mesma filosofia de fallback do `@retry`. |
| **State (dataclasses)** | 40% | `SLMissingState`, `ManualClosePendingState` — dataclasses que rastreiam **estado de posições individuais** (por `entry_order_id`). | `PluginRegistry` lifecycle (DISCOVERED → LOADED → ACTIVE → DEGRADED) é conceitual. `PluginRegistry` gerencia descoberta/registro, não transições de estado transacionais. Alinhamento é conceitual, não estrutural. |
| **Builder** | 30% | `GrafanaDashboardBuilder` (fluent API, retorna `self`). `DashboardSnapshotBuilder` (versão minimalista). | **Aspiracional** — `SignalResult` poderia usar Builder se campos opcionais crescerem. Sem implementação concreta na SPEC_033 v1.3. |
| **Registry** | 20% | — (verdadeiramente novo na SPEC_033). A SPEC v1.2 citava `_sl_missing_state` como equivalente, mas **dict de tracking de estado ≠ Registry**. | `PluginRegistry` — descoberta, registro, validação, health check. Separa lifecycle management de evaluation logic (SRP). **Genuinamente novo no projeto.** |

---

### 5.1 Interface `StrategyPlugin` (Template Method)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class SignalResult:
    direction: str | None       # "LONG", "SHORT", or None
    entry_price: float | None   # Preço de entrada calculado
    stop_loss: float | None     # Stop loss obrigatório
    take_profit: float | None   # Take profit (ex.: 2× risco)
    metadata: dict = field(default_factory=dict)
    # Metadata esperado para WilliamsStrategy:
    # {
    #   "confidence": float,        # 0.0 a 1.0
    #   "indicators": {
    #       "alligator_jaws": float,
    #       "alligator_teeth": float,
    #       "alligator_lips": float,
    #       "ao_value": float,
    #       "fractal_high": float,
    #       "fractal_low": float,
    #   },
    #   "warmup_candles_used": int,
    # }

    def __bool__(self) -> bool:
        """NullSignalResult é falsy; SignalResult real é truthy."""
        return self.direction is not None


# ── Compatibilidade retroativa ─────────────────────────────────────
# Direction e Signal eram exportados de signal_engine.py e importados por:
#   - src/trading/risk_manager.py
#   - src/trading/order_manager.py
#   - src/backtest/engine.py
#   - src/api/routes/onboarding.py
#
# Após a refatoração, signal_engine.py deve re-exportá-los como aliases
# para não quebrar imports existentes. A remoção definitiva fica para
# uma SPEC futura de limpeza de API.
# Direction = Literal["LONG", "SHORT"]  (mesmo tipo atual)


class NullSignalResult(SignalResult):
    """Null Object: representa ausência de sinal de forma explícita.

    Útil para chains (é falsy) e para logging (carrega reason na metadata).
    """
    direction: None = None
    entry_price: None = None
    stop_loss: None = None
    take_profit: None = None
    metadata: dict = field(default_factory=lambda: {"reason": "no_signal"})


class StrategyPlugin(ABC):
    """Template Method: evaluate() define o esqueleto; subclasses implementam ganchos.

    Alinhamento com Template Method do projeto:
    - `_create_order_with_protect()` em binance_client.py define esqueleto fixo (tenta com priceProtect → fallback)
      e delega a 3 callers concretos (stop_loss, take_profit, trailing_stop).
    - `StrategyPlugin.evaluate()` segue o mesmo padrão: esqueleto fixo (5 passos), subclasses implementam hooks.
    """

    def __init__(self, risk_reward_ratio: float = 2.0):
        """Inicializa plugin com parâmetros compartilhados.

        Args:
            risk_reward_ratio: Razão risco/retorno para cálculo de SL/TP (padrão 2.0).
                               Passado pelo SignalEngine ou PluginRegistry no momento do registro.
        """
        self._rrr = risk_reward_ratio

    @property
    @abstractmethod
    def name(self) -> str:
        """Nome único do plugin (ex.: 'williams', 'macd_crossover')."""

    async def evaluate(self, symbol: str, timeframe: str, df: pd.DataFrame) -> SignalResult:
        """Template Method — não sobrescrever diretamente.

        Subclasses sobrescrevem os ganchos _validate_input, _compute_indicators,
        _check_conditions, _calculate_targets e (opcional) _calculate_confidence.
        """
        validated_df = await self._validate_input(df)
        enriched = await self._compute_indicators(validated_df)
        direction = await self._check_conditions(enriched)
        if direction is None:
            return NullSignalResult(reason=f"{self.name}_no_opportunity")
        sl, tp = await self._calculate_targets(enriched, direction)
        confidence = await self._calculate_confidence(enriched, direction)
        return self._build_result(direction, sl, tp, confidence, enriched)

    # ── Ganchos para subclasses ─────────────────────────────────

    async def _validate_input(self, df: pd.DataFrame) -> pd.DataFrame:
        """Valida tamanho mínimo, colunas necessárias. Padrão: len >= warmup."""
        if len(df) < self.warmup_candles():
            raise ValueError(f"need at least {self.warmup_candles()} candles")
        return df

    @abstractmethod
    async def _compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula indicadores específicos da estratégia."""

    @abstractmethod
    async def _check_conditions(self, enriched: pd.DataFrame) -> str | None:
        """Retorna 'LONG', 'SHORT', ou None."""

    @abstractmethod
    async def _calculate_targets(
        self, enriched: pd.DataFrame, direction: str
    ) -> tuple[float, float]:
        """Retorna (stop_loss, take_profit).

        Nota de implementação: o WilliamsStrategy deve chamar a lógica existente
        extraída do SignalEngine._calculate_targets() (métodos estáticos), NÃO
        reimplementar o cálculo de SL/TP do zero. A extração é parte da subtask_05.
        """

    async def _calculate_confidence(self, enriched: pd.DataFrame, direction: str) -> float:
        """Padrão: 1.0. Subclasses podem sobrescrever."""
        return 1.0

    @abstractmethod
    def warmup_candles(self) -> int:
        """Quantos candles de warmup esta estratégia precisa."""

    def _build_result(self, direction, sl, tp, confidence, enriched) -> SignalResult:
        """Monta SignalResult com metadata."""
        return SignalResult(
            direction=direction,
            entry_price=float(enriched.iloc[-1]["close"]),
            stop_loss=sl,
            take_profit=tp,
            metadata={"confidence": confidence, "plugin": self.name},
        )
```

### 5.2 `PluginRegistry` — Registry Pattern

```python
class PluginRegistry:
    """Gerencia descoberta, registro e ciclo de vida de plugins.

    Responsabilidades:
    - Descobrir plugins via importlib.metadata.entry_points
    - Validar Regra Mestre (WilliamsStrategy sempre presente)
    - Envelopar com decorators (timeout, metrics, validação)
    - Manter health check dos plugins registrados

    Ordem dos decorators (de dentro para fora):
        plugin → TimeoutDecorator → ValidationDecorator → MetricsDecorator

    Justificativa: Timeout mais externo cobre todo o pipeline (validação + métricas incluídas).
    """

    def __init__(self, group: str = "phicube.strategies", timeout: float = 30.0):
        self._group = group
        self._timeout = timeout
        self._plugins: dict[str, PluginDecorator] = {}

    def discover_and_register_all(self) -> None:
        """Descobre entry_points, wrappa com decorators e registra.

        Protegido por try/except: se um plugin falhar no registro, os demais
        continuam sendo registrados. A falha é logada como warning.
        Se NENHUM plugin for carregado (incluindo Williams), um RuntimeError é
        levantado para evitar bot sem estratégia.
        """
        any_success = False
        for ep in entry_points(group=self._group):
            try:
                plugin_class = ep.load()
                plugin = plugin_class()
                self.register(plugin)
                any_success = True
            except Exception as exc:
                logger.warning("plugin_discovery_failed", name=ep.name, error=type(exc).__name__)
        if not any_success:
            raise RuntimeError("no_plugins_discovered")

    def register(self, plugin: StrategyPlugin) -> None:
        """Envelopa plugin com decorators e registra.

        Ordem: Timeout(Validation(Metrics(plugin))).
        Timeout é o mais externo para cobrir validação e métricas dentro do timeout.
        """
        if plugin.name == "williams":
            logger.warning("cannot_override_williams", name=plugin.name)
            return
        wrapped: StrategyPlugin = MetricsDecorator(plugin)
        wrapped = ValidationDecorator(wrapped)
        wrapped = TimeoutDecorator(wrapped, timeout=self._timeout)
        self._plugins[plugin.name] = wrapped

    def get(self, name: str) -> PluginDecorator | None:
        return self._plugins.get(name)

    @property
    def available(self) -> list[str]:
        return list(self._plugins.keys())

    def health_check(self) -> dict[str, bool]:
        """Retorna {plugin_name: True se respondeu, False se não}."""
        return {name: p.health() for name, p in self._plugins.items()}
```

### 5.4 `SignalEngine` — Chain of Responsibility (com PluginRegistry + NullSignalResult)

O `SignalEngine` é **stateless por design**: delega descoberta e ciclo de vida para `PluginRegistry`, e usa `NullSignalResult` em vez de `None` para simplificar a chain.

**Mudanças em relação ao design anterior:**
- `PluginRegistry` substitui `_load_plugins()` e `PluginProxy` manual
- `NullSignalResult` substitui `return None` — chain usa `if result:` (falsy check)
- Observer events substituem chamadas diretas de métricas no hot path
- Plugin loading é feito via `PluginRegistry.discover_and_register_all()`
- **`_last_evaluation` removido** — SignalEngine é stateless (INV-033-07)
- **`consume_last_evaluation()` removido** — substituído por Observer events

**Compatibilidade retroativa (imports):**
- `Direction` e `Signal` são re-exportados como aliases em signal_engine.py:
  ```python
  Direction = Literal["LONG", "SHORT"]
  # Signal mantido como type alias para compatibilidade com:
  #   - risk_manager.py (importa Signal)
  #   - order_manager.py (importa Direction)
  #   - backtest/engine.py
  #   - api/routes/onboarding.py
  ```
- Callers que usam `if result is not None:` devem migrar para `if result:` (aceita `NullSignalResult` como falsy).
- A remoção definitiva dos aliases será em SPEC futura.

```python
class SignalEngine:
    """Chain of Responsibility: plugin configurado → Williams fallback.

    Stateless: não mantém _last_evaluation. Audit trail via Observer events.
    """

    def __init__(
        self,
        risk_reward_ratio: float,
        settings: Settings | None = None,
        registry: PluginRegistry | None = None,
    ):
        self._rrr = risk_reward_ratio
        self._settings = settings
        self._registry = registry or PluginRegistry()
        self._listeners: dict[SignalEvent, list[Callable]] = {}

        if settings is not None:
            self._registry.discover_and_register_all()
            self._registry.validate_master()

    # ── Observer ──────────────────────────────────────────────────
    def on(self, event: SignalEvent, callback: Callable[[SignalEventData], None]) -> None:
        self._listeners.setdefault(event, []).append(callback)

    def _emit(self, event: SignalEvent, data: SignalEventData) -> None:
        for cb in self._listeners.get(event, []):
            try: cb(data)
            except Exception: logger.exception("observer_failed", event=event.value)

    # ── Chain of Responsibility ───────────────────────────────────
    async def evaluate(self, symbol: str, timeframe: str, df: pd.DataFrame) -> SignalResult:
        start = time.time()

        plugin_name = self._settings.SYMBOL_STRATEGY_MAP.get(symbol, self._settings.DEFAULT_STRATEGY)

        # Handle 1: Plugin configurado
        result = await self._try_plugin(plugin_name, symbol, timeframe, df)
        if result:
            self._emit(SignalEvent.DETECTED, SignalEventData(
                SignalEvent.DETECTED, symbol, timeframe, result, time.time() - start))
            return result

        # Handle 2: Williams fallback (Regra Mestre)
        if plugin_name != "williams":
            williams = self._registry.get("williams")
            if williams:
                result = await williams.evaluate(symbol, timeframe, df)
                if result:
                    self._emit(SignalEvent.DETECTED, SignalEventData(
                        SignalEvent.DETECTED, symbol, timeframe, result, time.time() - start))
                    return result

        no_signal = NullSignalResult(reason=f"no_plugin_signal:{plugin_name}")
        self._emit(SignalEvent.EVALUATED, SignalEventData(
            SignalEvent.EVALUATED, symbol, timeframe, no_signal, time.time() - start))
        return no_signal

    async def _try_plugin(self, name: str, symbol: str, timeframe: str, df: pd.DataFrame) -> SignalResult:
        plugin = self._registry.get(name)
        if plugin is None:
            return NullSignalResult(reason=f"plugin_not_found:{name}")
        return await plugin.evaluate(symbol, timeframe, df)
```

### 5.5 `src/config/settings.py` — novos campos

```python
SYMBOL_STRATEGY_MAP: dict[str, str] = {
    "BTCUSDT": "williams",
    "ETHUSDT": "williams",
    # Símbolos não listados usam DEFAULT_STRATEGY
}
DEFAULT_STRATEGY: str = "williams"
PLUGIN_TIMEOUT: float = 30.0  # segundos, usado pelo PluginProxy
```

---

## 6. Componentes

### 6.1 `src/strategy/plugin_base.py` — interface e dataclass

Contém: `SignalResult`, `StrategyPlugin(ABC)`.

### 6.2 `src/strategy/plugin_registry.py` — Registry Pattern

Contém: `PluginRegistry` — descoberta, registro, validação e health check de plugins.

### 6.3 `src/strategy/plugin_decorator.py` — Decorator Pattern

Contém: `PluginDecorator` (base), `TimeoutDecorator`, `MetricsDecorator`, `ValidationDecorator`.

### 6.4 `src/strategy/plugin_null.py` — Null Object Pattern

Contém: `NullSignalResult`.

### 6.5 `src/strategies/williams_strategy.py` — plugin concreto

**Performance requirements (validados em code review de otimização):**

1. **Fractal caching obrigatório** — `last_valid_fractal_high()` e `last_valid_fractal_low()` devem ser chamados **uma vez cada** por chamada de `evaluate()` e reutilizados nas branches long e short (INV-033-08). O código atual chama 4× por tick.

2. **DataFrame único** — Usar `compute_all_optimized()` (que faz 1 cópia de df) em vez de `compute_all()` atual (que faz 3 cópias). O indicador `fractals_inplace()` modifica o DataFrame por referência em vez de copiar.

3. **Sem estado entre chamadas** — A classe não deve ter `_last_evaluation` ou qualquer outro campo mutável tocado por `evaluate()` (INV-033-07).

**Requisitos de implementação:**

- **`risk_reward_ratio`** recebido via `__init__` (herdado de `StrategyPlugin.__init__(risk_reward_ratio)`)
- **`_calculate_targets()`** deve **extrair a lógica existente** do `SignalEngine._calculate_targets()` (métodos estáticos), não reimplementar do zero. A extração faz parte desta task — o código extraído pode ficar em `indicators.py` como função helper ou permanecer como static method no `SignalEngine`.
- **`_count_recent_crosses()`** deve ser implementado como helper em `indicators.py` (não existe atualmente) — conta cruzamentos do AO nos últimos N candles.

```python
class WilliamsStrategy(StrategyPlugin):
    name = "williams"
    # risk_reward_ratio herdado de StrategyPlugin.__init__(rrr)

    async def evaluate(self, symbol, timeframe, df) -> SignalResult:
        # Otimização: usar compute_all_optimized() — 1 cópia de df
        enriched = compute_all_optimized(df)

        # Otimização: cache fractal values uma vez
        fractal_high = last_valid_fractal_high(enriched)
        fractal_low = last_valid_fractal_low(enriched)
        # ^^^^ chamados 1× cada, reusados em ambas branches

        # ... lógica long/short (extraída do SignalEngine atual) ...

    def warmup_candles(self) -> int:
        return 34  # AO(5,34) = 34 períodos. Fonte: MetaTrader 5 docs

    async def _calculate_targets(self, enriched, direction) -> tuple[float, float]:
        """Delega para a lógica extraída do SignalEngine atual."""
        return calculate_sl_tp_from_indicators(
            enriched, direction, risk_reward_ratio=self._rrr,
            atr_column="atr",
            close_column="close",
        )

    async def _calculate_confidence(self, enriched, direction) -> float:
        """Confidence baseado em AO magnitude + divergência + distância fractal.
        
        Fórmula: ao_magnitude/atr (0.0-0.5) + ao_divergence (0.0-0.3) + fractal_dist (0.0-0.2)
        Usa _count_recent_crosses() de indicators.py.
        """
        ...
```

### 6.6 `src/strategies/__init__.py` — entry_points discovery

Registo via `pyproject.toml`:

```toml
[project.entry-points."phicube.strategies"]
williams = "src.strategies.williams_strategy:WilliamsStrategy"
```

### 6.7 `src/strategy/signal_engine.py` — modificado

Usa `PluginRegistry`, `PluginDecorator`, `NullSignalResult` e Observer events conforme 5.4.

---

## 7. Invariantes

| ID | Invariante |
|----|-----------|
| INV-033-01 | `SignalEngine.evaluate()` sempre retorna `SignalResult` ou `None` — nunca lança exceção |
| INV-033-02 | Plugin desconhecido → fallback para `DEFAULT_STRATEGY` |
| INV-033-03 | `WilliamsStrategy` ocupa slot `"williams"` — imutável, não sobrescritível por colisão |
| INV-033-04 | Falha em um plugin (exceção ou timeout) não afeta avaliação de outros símbolos |
| INV-033-05 | Todo `evaluate()` de plugin passa por `PluginProxy` com timeout configurável |
| INV-033-06 | Cada `TradingMonitor` possui sua própria instância de `SignalEngine` — nenhum estado mutável é compartilhado entre monitores |
| INV-033-07 | `SignalEngine` não mantém `_last_evaluation` — é stateless; audit trail via Observer events |
| INV-033-08 | `WilliamsStrategy._calculate_confidence()` deve usar os valores cacheados de fractais (não recalcular 4× por tick) |
| INV-033-09 | `evaluate()` sempre retorna `SignalResult` (nunca `None`) — `NullSignalResult` para casos sem sinal |
| INV-033-10 | `PluginRegistry` gerencia descoberta e ciclo de vida; `SignalEngine` só faz avaliação (SRP) |
| INV-033-11 | Todo plugin segue o Template Method: `_validate_input` → `_compute_indicators` → `_check_conditions` → `_calculate_targets` |

---

## 8. Testes

| ID | Descrição | Prioridade |
|----|-----------|-----------|
| TEST_033_01 | `WilliamsStrategy` retorna `SignalResult` válido com dados conhecidos | Alta |
| TEST_033_02 | Discovery via entry_points carrega WilliamsStrategy | Alta |
| TEST_033_03 | `SYMBOL_STRATEGY_MAP` direciona para plugin correto | Alta |
| TEST_033_04 | Símbolo não mapeado usa `DEFAULT_STRATEGY` | Alta |
| TEST_033_05 | Plugin mock retorna sinal consumido pelo SignalEngine | Alta |
| TEST_033_06 | Plugin com exceção → Proxy retorna None, não quebra outros | Alta |
| TEST_033_07 | Plugin lento (`asyncio.sleep(999)`) → Proxy timeout retorna None | Alta |
| TEST_033_08 | Regra Mestre: Chain cai no Williams após plugin configurado falhar | Alta |
| TEST_033_09 | WilliamsStrategy não pode ser sobrescrito por colisão de nome | Média |
| TEST_033_10 | Dois `TradingMonitor` com instâncias diferentes de `SignalEngine` — avaliações simultâneas não contaminam estados entre si | Alta |
| TEST_033_11 | `WilliamsStrategy.evaluate()` não recalcula `last_valid_fractal_high()` e `last_valid_fractal_low()` mais de uma vez por chamada | Média |
| TEST_033_12 | `PluginRegistry.discover_and_register_all()` carrega WilliamsStrategy do entry_point e wrappa com decorators | Alta |
| TEST_033_13 | `NullSignalResult` é falsy em `bool()`; `SignalResult` com direction="LONG" é truthy | Média |
| TEST_033_14 | `TimeoutDecorator` retorna `NullSignalResult(reason=...)` em vez de `None` ao exceder timeout | Alta |
| TEST_033_15 | Plugin que implementa Template Method corretamente produz `SignalResult` via `_build_result()` | Média |

---

## 9. Arquivos

| Arquivo | Mudança |
|---------|---------|
| `src/strategy/plugin_base.py` | **Criado** — `SignalResult`, `NullSignalResult`, `StrategyPlugin(ABC)` com Template Method |
| `src/strategy/plugin_registry.py` | **Criado** — `PluginRegistry`: descoberta, registro, validação, health check |
| `src/strategy/plugin_decorator.py` | **Criado** — `PluginDecorator` (base), `TimeoutDecorator`, `MetricsDecorator` |
| `src/strategies/__init__.py` | **Criado** — entry_points discovery |
| `src/strategies/williams_strategy.py` | **Criado** — `WilliamsStrategy` (código extraído do SignalEngine, fractal caching, stateless) |
| `src/strategy/signal_engine.py` | **Modificado** — Chain of Responsibility + PluginProxy. `_last_evaluation` removido (stateless). `consume_last_evaluation()` removido. |
| `src/strategy/indicators.py` | **Modificado** — `compute_all()` otimizado para 1 cópia de DataFrame (vs 3 atuais). Inclui `fractals_inplace()` para evitar cópias extras. |
| `src/config/settings.py` | **Modificado** — `SYMBOL_STRATEGY_MAP`, `DEFAULT_STRATEGY`, `PLUGIN_TIMEOUT` |
| `src/main.py` | **Modificado** — `_build_monitor()` cria `SignalEngine(...)` por monitor (remove instância compartilhada). `RuntimeMonitorRegistry.__init__` não recebe mais `signal_engine`. |
| `pyproject.toml` | **Modificado** — entry_points `phicube.strategies` |
| `tests/strategy/test_plugin_base.py` | **Criado** — TEST_033_01, 02 |
| `tests/strategy/test_plugin_discovery.py` | **Criado** — TEST_033_03 a 09 |
| `tests/strategy/test_plugin_patterns.py` | **Criado** — TEST_033_10 a 15 |

---

## 10. Riscos

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| Plugin bugado retorna sinais falsos continuamente | Alto | Proxy captura exceções + timeout. Testes obrigatórios por plugin. |
| Plugin nunca usado ocupa memória | Baixo | Log warning se inativo >30 dias. Remoção manual. |
| Colisão de nome plugin sobrescreve Williams | Alto | WilliamsStrategy tem slot protegido — loga erro e ignora. |
| Performance de 10+ plugins carregados | Baixo | Discovery é O(N) na inicialização, O(1) no hot path. Irrelevante. |
| SignalEngine compartilhado entre monitores corrompe audit trail | **Crítico** | Cada TradingMonitor tem sua própria instância (INV-033-06). SignalEngine é stateless (INV-033-07). Nenhum lock necessário. |
| Plugin não segue Template Method — esquece de calcular SL/TP ou confidence | Alto | Template Method na classe base garante estrutura. Testes de conformidade (TEST_033_15). |
| Decorator chain muito longa degrada performance | Baixo | Limite de 5 decorators documentado. `health_check()` monitora latência. |
| NullSignalResult confundido com sinal real em consumidores | Médio | `__bool__` é falsy. Consumidores devem usar `if result:` em vez de `if result is not None:`. |

---

## 11. Definition of Done

### Implementação
- [ ] `SignalResult` + `NullSignalResult` definidos (Null Object Pattern)
- [ ] `StrategyPlugin` com Template Method: `evaluate()` + 5 ganchos, construtor aceita `risk_reward_ratio`
- [ ] `PluginRegistry` com `discover_and_register_all()`, `get()`, `validate_master()`, `health_check()`
- [ ] `TimeoutDecorator` implementa timeout com `NullSignalResult` (não `None`)
- [ ] `MetricsDecorator` emite métricas Prometheus (substitui chamadas diretas)
- [ ] `WilliamsStrategy` implementado como plugin (warmup=34, Template Method, fractal caching, `risk_reward_ratio` no construtor)
- [ ] `_calculate_targets()` extraído do SignalEngine atual para helper reutilizável (não duplicado no plugin)
- [ ] `_count_recent_crosses()` implementado em `indicators.py` como helper
- [ ] Chain of Responsibility: plugin config → Williams fallback (com `NullSignalResult`)
- [ ] SignalEngine **stateless** — `_last_evaluation` removido, `consume_last_evaluation()` removido, Observer events para audit trail
- [ ] `Direction` e `Signal` mantidos como re-exports em `signal_engine.py` (compatibilidade retroativa)
- [ ] Todos os callers de `evaluate()` migrados de `is not None` para `if result:`
- [ ] Cada `TradingMonitor` com sua própria instância de `SignalEngine` (INV-033-06)
- [ ] `RuntimeMonitorRegistry.__init__` aceita `signal_engine=None` como parâmetro opcional (depreciação gradual)
- [ ] `main.py:743` — instância compartilhada de `SignalEngine` removida
- [ ] Config `SYMBOL_STRATEGY_MAP`, `DEFAULT_STRATEGY`, `PLUGIN_TIMEOUT`
- [ ] `compute_all()` mantido como wrapper que chama `compute_all_optimized()` (retrocompatibilidade)
- [ ] `discover_and_register_all()` protegido com try/except — levanta `RuntimeError` se nenhum plugin carregado

### Testes
- [ ] Todos os testes marcados com `pytest.mark.timeout(2)` para fail rápido
- [ ] TEST_033_01 a 15 passando com `pytest tests/strategy/ -v`

### Qualidade
- [ ] `ruff check src/ tests/` limpo

---

## 12. Histórico

- **2026-05-10:** Criação da SPEC_033 v1.0 (Rascunho inicial)
- **2026-05-13:** Refinamento Time A — 6 decisões (warmup=34, SignalResult c/ SL/TP, entry_points, Proxy, Chain of Responsibility, confidence via metadata). Status → Em Refinamento.
- **2026-05-13:** Code Review de otimização — adicionado SignalEngine stateless por monitor (INV-033-06, INV-033-07, INV-033-08), removido `_last_evaluation`, fractal caching no WilliamsStrategy. Versão 1.2.
- **2026-05-13:** Análise de padrões de design — adicionados 5 padrões complementares: Registry (4.5), Null Object (4.6), Decorator (4.7), Template Method (4.8), Observer (4.9). Mapa de padrões do projeto vs SPEC_033 (4.10). SignalEngine atualizado para usar PluginRegistry + NullSignalResult + Observer. Versão 1.3.
- **2026-05-13:** Ajuste pós-análise de padrões — Mapa 4.10 corrigido com porcentagens de força de alinhamento; StrategyPlugin aceita `risk_reward_ratio`; WilliamsStrategy documenta extração de `_calculate_targets` e `_count_recent_crosses`; SignalEngine adiciona re-export de `Direction`/`Signal` e `signal_engine=None` opcional; DoD expandido de 14 para 20 itens; tasks atualizadas com descobertas da análise. Versão 1.4.
- **2026-05-13:** Implementação Time B (Batches 1-3). Código: PluginRegistry wired em main.py, SignalEngine removido de RuntimeMonitorRegistry, _compute_indicators skip se colunas existem, Chain-of-Responsibility com handler result tracking, TimeoutDecorator com ThreadPoolExecutor reutilizável, PluginDecorator.name fix, NullSignalReason removido. Testes: 90 testes (16 SPEC_033 + 54 legados + 20 corpus). SPEC_013 corpus compatível (compute_all_optimized via test helper). Versão 1.5.
