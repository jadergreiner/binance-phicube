# SPEC_033 — Arquitetura de Plugins de Estratégia

**ID:** SPEC_033
**Título:** Arquitetura de Plugins de Estratégia
**Data:** 2026-05-10
**Status:** Rascunho
**Versão:** 1.0
**Dependências:** SPEC_013 (validação signal engine)
**PRD §:** Fase 2 — "Framework de estratégias plugáveis"

---

## 1. Objetivo

Substituir o acoplamento rígido entre `SignalEngine` e a lógica BO Williams por uma arquitetura de plugins que permita carregar, testar e alternar entre múltiplas estratégias sem modificar o core do bot.

O `SignalEngine` atual eval hardcoded da estratégia Phicube. Com plugins, o operador pode:
- Rodar estratégias diferentes por símbolo
- A/B testar estratégias em paralelo
- Adicionar nova estratégia sem reiniciar o container

---

## 2. Escopo

### Dentro do escopo
- Interface abstrata `StrategyPlugin` com métodos `evaluate()` e `metadata()`
- Implementação da estratégia Phicube como plugin concreto (`WilliamsStrategy`)
- Loader dinâmico que descobre plugins no diretório `src/strategies/`
- Config `SYMBOL_STRATEGY_MAP` mapeando símbolo → plugin name
- Fallback para estratégia default se não configurada
- Testes com plugin mock

### Fora do escopo
- Hot-reload de plugins sem restart (será SPEC futura)
- Marketplace de estratégias
- Interface visual para seleção de estratégia

---

## 3. User Stories

### US-033-01 — Plugin carregado por config
**Como** operador,
**quero** configurar `SYMBOL_STRATEGY_MAP = {"BTCUSDT": "williams", "ETHUSDT": "williams"}`,
**para** que cada símbolo use a estratégia desejada.

**Critério de aceite:**
- `SignalEngine` carrega plugin correto por símbolo
- Se símbolo não mapeado, usa default

### US-033-02 — Nova estratégia = novo arquivo
**Como** desenvolvedor,
**quero** criar `src/strategies/macd_strategy.py` implementando `StrategyPlugin`,
**para** adicionar estratégia sem modificar SignalEngine.

**Critério de aceite:**
- Plugin descoberto automaticamente ao colocar no diretório
- `evaluate()` chamado com mesmos parâmetros que a engine atual

---

## 4. Modelo de Dados

### Interface `StrategyPlugin`

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class SignalResult:
    direction: str | None  # "LONG", "SHORT", or None
    confidence: float       # 0.0 a 1.0
    metadata: dict          # Dados extras (indicadores usados, etc.)

class StrategyPlugin(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Nome único do plugin (ex.: 'williams', 'macd_crossover')."""

    @abstractmethod
    async def evaluate(self, symbol: str, timeframe: str, df: pd.DataFrame) -> SignalResult:
        """Avalia estratégia e retorna sinal."""

    @abstractmethod
    def warmup_candles(self) -> int:
        """Quantos candles de warmup esta estratégia precisa."""
```

### `SignalEngine` modificado

```python
class SignalEngine:
    def __init__(self, settings: Settings):
        self.plugins: dict[str, StrategyPlugin] = {}
        self._load_plugins()

    def _load_plugins(self) -> None:
        """Descobre plugins em src/strategies/ via entry_points ou import scan."""

    async def evaluate(self, symbol: str, timeframe: str, df: pd.DataFrame) -> SignalResult:
        plugin_name = settings.SYMBOL_STRATEGY_MAP.get(symbol, "default")
        plugin = self.plugins[plugin_name]
        return await plugin.evaluate(symbol, timeframe, df)
```

---

## 5. Componentes

### 5.1 `src/strategy/plugin_base.py` — interface

```python
class StrategyPlugin(ABC):
    """Base class para todos os plugins de estratégia."""
```

### 5.2 `src/strategies/williams_strategy.py` — plugin concreto

```python
class WilliamsStrategy(StrategyPlugin):
    name = "williams"

    async def evaluate(self, symbol, timeframe, df) -> SignalResult:
        # Código atual do SignalEngine.evaluate()
        ...

    def warmup_candles(self) -> int:
        return 26  # BB period + safe margin
```

### 5.3 `src/strategies/__init__.py` — descoberta automática

```python
import importlib
import pkgutil
from src.strategy.plugin_base import StrategyPlugin

def discover_plugins() -> dict[str, StrategyPlugin]:
    plugins = {}
    for module_info in pkgutil.iter_modules(["src/strategies"]):
        module = importlib.import_module(f"src.strategies.{module_info.name}")
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and issubclass(attr, StrategyPlugin) and attr is not StrategyPlugin:
                instance = attr()
                plugins[instance.name] = instance
    return plugins
```

### 5.4 `src/config/settings.py` — novo campo

```python
SYMBOL_STRATEGY_MAP: dict[str, str] = {
    "BTCUSDT": "williams",
    "ETHUSDT": "williams",
    # Símbolos não listados usam "default"
}
DEFAULT_STRATEGY: str = "williams"
```

---

## 6. Invariantes

| ID | Invariante |
|----|-----------|
| INV-033-01 | `SignalEngine.evaluate()` sempre retorna `SignalResult` — nunca `None` |
| INV-033-02 | Plugin desconhecido → fallback para `DEFAULT_STRATEGY` |
| INV-033-03 | Cada plugin tem `name` único — colisão loga warning e usa o último |
| INV-033-04 | Falha em um plugin não afeta avaliação de outros símbolos |

---

## 7. Testes

| ID | Descrição |
|----|-----------|
| TEST_033_01 | Plugin WilliamsStrategy retorna `SignalResult` válido com dados conhecidos |
| TEST_033_02 | Discovery carrega WilliamsStrategy do diretório |
| TEST_033_03 | SYMBOL_STRATEGY_MAP redireciona para plugin correto |
| TEST_033_04 | Símbolo não mapeado usa DEFAULT_STRATEGY |
| TEST_033_05 | Plugin mock retorna sinal e é consumido por SignalEngine |
| TEST_033_06 | Plugin com erro não afeta outros símbolos |

---

## 8. Arquivos

| Arquivo | Mudança |
|---------|---------|
| `src/strategy/plugin_base.py` | Criado — classe abstrata `StrategyPlugin`, `SignalResult` |
| `src/strategies/__init__.py` | Criado — `discover_plugins()` |
| `src/strategies/williams_strategy.py` | Criado — `WilliamsStrategy` (código extraído do SignalEngine) |
| `src/strategy/signal_engine.py` | Modificado — usar `discover_plugins()`, delegar `evaluate` |
| `src/config/settings.py` | Modificado — `SYMBOL_STRATEGY_MAP`, `DEFAULT_STRATEGY` |
| `tests/strategy/test_plugin_base.py` | Criado — TEST_033_01, 02 |
| `tests/strategy/test_plugin_discovery.py` | Criado — TEST_033_03 a 06 |

---

## 9. Definition of Done

- [ ] Interface `StrategyPlugin` definida com `evaluate()`, `name`, `warmup_candles()`
- [ ] `WilliamsStrategy` implementado como plugin (extraído do SignalEngine)
- [ ] Descoberta automática de plugins funcional
- [ ] Config mapeia símbolo → plugin com fallback
- [ ] TEST_033_01 a 06 passando
- [ ] `ruff check src/ tests/` limpo
