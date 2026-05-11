# SPEC_030 — Saída Dinâmica: Trailing Stop e Take-Profit Parcial

**ID:** SPEC_030
**Título:** Saída Dinâmica: Trailing Stop e Take-Profit Parcial
**Data:** 2026-05-10
**Status:** Rascunho
**Versão:** 1.0
**Dependências:** SPEC_006 (métricas), SPEC_022 (regras de risco)
**PRD §:** Fase 2 — "Estratégia de saída avançada"

---

## 1. Objetivo

Atualmente o bot usa SL e TP fixos calculados na abertura da posição. Esta SPEC adiciona dois mecanismos de saída dinâmica:
1. **Trailing Stop Progressivo** — SL que acompanha o preço a favor, travando lucro
2. **Take-Profit Parcial** — Fechamento em lotes (ex.: 50% no TP1, 50% no TP2)

O operador pode combinar ou usar apenas SL fixo original (modo legacy).

---

## 2. Escopo

### Dentro do escopo
- Trailing stop com `activation_threshold` (% a partir da entrada) e `trail_distance` (%)
- TP parcial em até 3 níveis com `partial_qty_pct` por nível
- Modo legacy (SL/TP fixo atual = default) para backward compatibility
- Configuração por símbolo com fallback para config global
- Integração com `OrderManager` para envio de ordens condicionais
- Logging de ativação de trailing e execução de TP parcial

### Fora do escopo
- Re-entrada após TP parcial (será SPEC separada)
- Cancelamento de trailing stop já enviado (DD-002: nunca recolocar SL)
- Gestão visual no frontend

---

## 3. User Stories

### US-030-01 — Trailing Stop automático
**Como** operador,
**quero** configurar trailing stop que ativa quando o lucro atinge X%,
**para** proteger ganhos sem intervenção manual.

**Critério de aceite:**
- SL fixo inicial enviado na abertura
- Quando preço atinge `activation_threshold`, novo SL é enviado a `trail_distance` do preço atual
- SL nunca é recolocado se mercado reverter (DD-002)
- Log: `"Trailing ativado para {symbol}: SL ajustado para {price}"`

### US-030-02 — Take-profit parcial escalonado
**Como** operador,
**quero** configurar TP1=2% (50%) e TP2=4% (50%),
**para** realizar lucro parcial e deixar posição correr.

**Critério de aceite:**
- TP1 executado: 50% da quantidade fechada, posição reduzida
- TP2 executado: 50% restante fechado
- SL ajustado para break-even após TP1 (proteção)
- Log: `"TP1 executado {symbol}: fechado {qty} @ {price}"`

---

## 4. Modelo de Dados

### Config (`src/config/settings.py`)

```python
# Exit strategy
EXIT_STRATEGY: str = "fixed"           # "fixed", "trailing", "partial", "trailing+partial"

# Trailing stop
TRAILING_ACTIVATION_PCT: float = 1.0    # Ativa quando lucro >= 1%
TRAILING_DISTANCE_PCT: float = 0.5      # SL fica a 0.5% do melhor preço

# Partial TP (até 3 níveis)
TP_LEVELS: list[dict] = [
    {"pct": 2.0, "qty_pct": 50},         # TP1: 2%, vende 50%
    {"pct": 4.0, "qty_pct": 50},         # TP2: 4%, vende 50%
]
```

### Modelo de posição estendido

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `exit_strategy` | `str` | Estratégia usada na abertura |
| `trailing_active` | `bool` | Se trailing stop foi ativado |
| `best_price_seen` | `float` | Melhor preço desde abertura |
| `remaining_qty` | `float` | Quantidade ainda aberta (após TP parciais) |
| `tp_executed` | `list[dict]` | Histórico de TP parciais |
| `original_entry_qty` | `float` | Quantidade original da posição |

---

## 5. Componentes

### 5.1 `src/trading/order_manager.py` — extensão

```python
class OrderManager:
    async def open_position_with_exit_strategy(
        self, symbol: str, direction: str, qty: float,
        entry_price: float, sl_price: float, tp_prices: list[float],
        exit_strategy: str
    ) -> str | None:
        """Abre posição e configura estratégia de saída."""

    async def check_trailing_stop(
        self, symbol: str, current_price: float
    ) -> None:
        """Verifica e atualiza trailing stop se aplicável."""

    async def check_partial_tp(
        self, symbol: str, current_price: float
    ) -> None:
        """Verifica e executa TP parcial se aplicável."""
```

### 5.2 Algoritmo de Trailing Stop

```
A cada tick do loop de monitoramento (5min):
  Para cada posição com exit_strategy contendo "trailing":
    Se NOT trailing_active:
      Se lucro_float >= activation_threshold:
        trailing_active = True
        novo_sl = current_price * (1 - trail_distance)  # LONG
        Enviar ordem de SL no novo preço (cancelar SL antigo?)
        ❌ NÃO — DD-002 proíbe: SL nunca é recolocado.
        ✅ Enviar ordem de TAKE_PROFIT_LIMIT para fechar com lucro.
    Se trailing_active:
      Se current_price > best_price_seen:
        best_price_seen = current_price
        # Apenas registra — SL não é movido (DD-002)
```

> **Nota:** DD-002 (SPEC_022) determina que stop-loss nunca é recolocado automaticamente. O trailing stop funciona via **take-profit dinâmico** (ordem limit de venda que acompanha o preço), não movendo o SL original.

### 5.3 Algoritmo de TP Parcial

```
Na abertura:
  Calcular quantidades: qty_tp1 = total_qty * tp1.qty_pct / 100
                         qty_tp2 = total_qty * tp2.qty_pct / 100
  Enviar TP1 como take_profit_limit com qty_tp1
  Enviar TP2 como take_profit_limit com qty_tp2
  Restante da posição mantém SL fixo original

Ao executar TP1:
  Registrar em tp_executed
  Ajustar SL para entry_price (break-even) na quantidade remanescente
```

---

## 6. Invariantes

| ID | Invariante |
|----|-----------|
| INV-030-01 | SL fixo inicial nunca é removido ou afastado (DD-002) |
| INV-030-02 | Soma das quantidades dos TP parciais <= quantidade original |
| INV-030-03 | `activation_threshold` > `trail_distance` (senão ativa na abertura) |
| INV-030-04 | Posição só tem trailing ativo se `exit_strategy` contém "trailing" |
| INV-030-05 | TP parcial só reduz posição — nunca aumenta |

---

## 7. Testes

| ID | Descrição |
|----|-----------|
| TEST_030_01 | Trailing não ativa antes de atingir `activation_threshold` |
| TEST_030_02 | Trailing envia take-profit dinâmico após threshold |
| TEST_030_03 | TP1 executado → qty reduzida, SL ajustado para break-even |
| TEST_030_04 | TP1 + TP2 executados → posição zerada |
| TEST_030_05 | Exit strategy = "fixed" → comportamento atual (sem trailing/partial) |
| TEST_030_06 | SL original nunca é movido ou cancelado (DD-002) |

---

## 8. Arquivos

| Arquivo | Mudança |
|---------|---------|
| `src/config/settings.py` | Modificado — `EXIT_STRATEGY`, `TRAILING_*`, `TP_LEVELS` |
| `src/trading/position_model.py` | Modificado — novos campos `exit_strategy`, `trailing_active`, etc. |
| `src/trading/order_manager.py` | Modificado — `open_position_with_exit_strategy`, `check_trailing_stop`, `check_partial_tp` |
| `src/main.py` | Modificado — chamar `check_trailing_stop` e `check_partial_tp` no loop |
| `tests/trading/test_exit_strategies.py` | Criado — TEST_030_01 a 06 |

---

## 9. Definition of Done

- [ ] Trailing stop funcional com take-profit dinâmico (respeitando DD-002)
- [ ] TP parcial com 2+ níveis configuráveis
- [ ] Modo legacy (`fixed`) mantém comportamento atual
- [ ] Logs de ativação e execução registrados via structlog
- [ ] TEST_030_01 a 06 passando
- [ ] `ruff check src/ tests/` limpo
