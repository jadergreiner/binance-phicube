# SPEC_030 — Saída Dinâmica: Trailing Stop e Take-Profit Parcial

**ID:** SPEC_030
**Título:** Saída Dinâmica: Trailing Stop e Take-Profit Parcial
**Data:** 2026-05-11
**Status:** Aprovado
**Versão:** 2.0
**Dependências:** SPEC_006 (métricas), SPEC_022 (regras de risco, DD-002)
**PRD §:** Fase 2 — "Estratégia de saída avançada"
**Refinamento:** `refinamento-2026-05-11.md` (8 decisões D-001 a D-008, convergência)

---

## Histórico de Revisão

| Versão | Data | Status | Descrição |
|--------|------|--------|-----------|
| 1.0 | 2026-05-10 | Rascunho | Proposta inicial com trailing via TAKE_PROFIT_LIMIT móvel e reenvio de SL pós-TP1 |
| 2.0 | 2026-05-11 | **Aprovado** | Refinamento completo: TP parcial via reduceOnly nativas (V1), TRAILING_STOP_MARKET nativo (V2), rejeitado reenvio de SL, D-001 a D-008 |

---

## 1. Objetivo

Atualmente o bot usa SL e TP fixos calculados na abertura da posição. Esta SPEC adiciona dois mecanismos de saída dinâmica:

1. **Take-Profit Parcial (V1)** — Fechamento em lotes via ordens reduceOnly nativas enviadas na abertura. Zero lógica de pós-processamento. A exchange Binance gerencia o ajuste automático das ordens remanescentes.
2. **Trailing Stop Nativo (V2)** — TRAILING_STOP_MARKET via Algo Order API (`POST /fapi/v1/algo`). Chamada direta, sem dependência de ccxt.

O modo legado `"fixed"` é o default e mantém o comportamento atual inalterado.

---

## 2. Escopo

### Dentro do escopo

**V1 — TP Parcial (obrigatório):**
- TP parcial com até 3 níveis configuráveis, ordens `TAKE_PROFIT_MARKET` com `reduceOnly=true`
- STOP_MARKET (SL fixo) + TP levels enviados juntos na abertura da posição
- NENHUMA lógica de pós-processamento (exchange gerencia ajuste)
- Config validation no startup com erro fatal (padrão SPEC_022)
- RRR médio ponderado pela quantidade de cada nível
- Logging de qual nível executou, preço, quantidade remanescente e condições de mercado
- Compatibilidade com modo simulation (`SimulatedBinanceClient`)

**V2 — Trailing Stop (condicional à verificação técnica):**
- `TRAILING_STOP_MARKET` nativo via Algo Order API (`POST /fapi/v1/algo`)
- `callbackRate` fixo configurável por símbolo
- `activatePrice` para ativação após lucro mínimo
- Chamada REST direta ao endpoint (não via ccxt)

**Geral:**
- Estratégia de saída configurável por símbolo com fallback global
- Modo legado `"fixed"` (SL + TP fixos = comportamento atual) como default

### Fora do escopo

- Re-entrada após TP parcial (será SPEC separada)
- Cancelamento de trailing stop já enviado (DD-002: stop-loss nunca é recolocado)
- Trailing adaptativo por ATR (D-005 rejeitado — hipótese para ciclo futuro)
- Gestão visual no frontend
- Modo `"partial+trailing"` combinado (futuro)

---

## 3. User Stories

### US-030-01 — Trailing Stop automático via TRAILING_STOP_MARKET nativo

**Como** operador,
**quero** configurar trailing stop que ativa automaticamente quando o lucro atinge X%,
**para** proteger ganhos sem intervenção manual nem risco de gap.

**Critério de aceite:**
- Na abertura, TRAILING_STOP_MARKET enviado com `activatePrice` e `callbackRate`
- Exchange ativa o trailing quando preço atinge `activation_threshold`
- Exchange ajusta o stop automaticamente conforme o preço sobe
- Zero reenvio de ordens pelo bot — sem risco de gap (ordem MARKET)
- Log: `"TRAILING_STOP criado para {symbol}: activatePrice={price}, callbackRate={rate}"`
- Log na ativação: `"TRAILING_STOP ativado para {symbol}"`

### US-030-02 — Take-profit parcial escalonado sem reenvio de SL

**Como** operador,
**quero** configurar TP1=2% (50%) e TP2=4% (50%),
**para** realizar lucro parcial sem reintroduzir risco operacional de reenvio de SL.

**Critério de aceite:**
- TP1 executado: 50% da quantidade fechada, posição reduzida, SL remanescente intacto
- TP2 executado: 50% restante fechado
- SL original NUNCA é reenviado ou ajustado (DD-002)
- Log: `"TP executado {symbol}: nível={level}, fechado {qty} @ {price}, restante {remaining}"`
- Exchange ajusta automaticamente as ordens reduceOnly remanescentes

---

## 4. Modelo de Dados

### Config (`src/config/settings.py`)

```python
# Estratégia de saída
EXIT_STRATEGY: str = "fixed"
# "fixed"   → comportamento atual (SL + TP fixos) — DEFAULT
# "partial" → TP parcial com N níveis (V1)
# "trailing" → trailing stop nativo via TRAILING_STOP_MARKET (V2)
# "partial+trailing" → futuro

# TP Parcial (V1) — até 3 níveis
# Cada nível: {"pct": 2.0, "qty_pct": 50}
#   pct: percentual de lucro alvo (ex: 2.0 = 2%)
#   qty_pct: percentual da quantidade a fechar (ex: 50 = 50%)
# sum(qty_pct) <= 100
# 1 <= len(tp_levels) <= 3
TP_LEVELS: list[dict] = [
    {"pct": 2.0, "qty_pct": 50},   # Nível 1: TP 2%, fecha 50%
    {"pct": 4.0, "qty_pct": 50},   # Nível 2: TP 4%, fecha 50%
]

# Trailing Stop (V2) — nativo TRAILING_STOP_MARKET
TRAILING_ACTIVATION_PCT: float = 1.0    # Ativa trailing quando lucro >= 1%
TRAILING_CALLBACK_RATE: float = 0.5      # callbackRate = 0.5% (Algo Order API)
```

### Config validation no startup (erro fatal)

Se `exit_strategy` contém `"partial"`:
- `1 <= len(tp_levels) <= 3`
- Cada `lvl.qty_pct > 0`
- Cada `lvl.pct > 0`
- `sum(lvl.qty_pct) <= 100`

Se `exit_strategy` contém `"trailing"`:
- `activation_threshold > trail_distance` (senão ativa na abertura)

### Modelo de posição (`Trade`)

| Campo | Tipo | Descrição | Obrigatório |
|-------|------|-----------|-------------|
| `exit_strategy` | `str` | Estratégia usada na abertura | V1 |
| `tp_levels` | `list[dict]` | Níveis de TP configurados | V1 |
| `sl_price` | `float` | Preço do stop-loss (já existente) | Existente |
| `tp_prices` | `list[float]` | Preços alvo de cada nível (calculados na abertura) | V1 |

> ⚠️ NENHUM campo de estado pós-abertura é necessário. A exchange gerencia ordens reduceOnly, quantidades remanescentes e execução de trailing. O bot NÃO persiste `remaining_qty`, `best_price_seen` ou `tp_executed`.

---

## 5. Componentes

### 5.1 Algoritmo de TP Parcial (V1)

```
Na abertura (execute()):
  1. Calcular SL fixo (fractal — como hoje)
  2. Para cada level em tp_levels:
       qty_level = total_qty * level.qty_pct / 100
  3. Enviar ordem MARKET de entrada (como hoje)
  4. Enviar STOP_MARKET (SL) com reduceOnly=true, qty = total_qty
  5. Para cada level em tp_levels:
       Enviar TAKE_PROFIT_MARKET com reduceOnly=true, qty = qty_level
  ⚠️ NENHUMA lógica de pós-processamento
  🔒 DD-002 respeitado: SL original permanece intocado
  💡 Ordem dos TPs não importa — exchange gerencia corretamente
```

**Arquivo:** `src/trading/order_manager.py` — método `execute()` modificado.

### 5.2 Algoritmo de Trailing Stop (V2 — condicional)

```
Na abertura (execute()):
  1. Calular SL/entrada (como hoje)
  2. Enviar ordem MARKET de entrada (como hoje)
  3. Chamada REST ao POST /fapi/v1/algo:
       symbol: symbol
       side: SELL (LONG) / BUY (SHORT)
       quantity: total_qty
       activatePrice: entry_price * (1 + activation_threshold)  # LONG
       callbackRate: trailing_distance
       reduceOnly: false
  4. Log: "TRAILING_STOP criado: {symbol}, activatePrice={price}, callbackRate={rate}"
  ⚠️ TRAILING_STOP_MARKET substitui o SL fixo
  🔒 DD-002 respeitado: stop é gerenciado pela exchange, não reenviado pelo bot
```

**Arquivo:** `src/exchange/binance_client.py` — novo método `create_trailing_stop_order()`.
**Endpoint:** `POST /fapi/v1/algo` (REST direta, não via ccxt).

### 5.3 SimulatedBinanceClient

O `SimulatedBinanceClient` (modo simulation) deve aceitar múltiplas ordens reduceOnly simultâneas (TP1 + TP2 + SL) e simulá-las localmente:

- Na abertura: registrar todas as ordens reduceOnly
- A cada tick de simulação: verificar se preço atingiu TP levels
- Ao executar TP: reduzir posição simulada, manter SL original
- Logging idêntico ao modo real

---

## 6. Invariantes

| ID | Invariante | Origem |
|----|-----------|--------|
| INV-030-01 | SL fixo inicial nunca é removido ou afastado | DD-002 (SPEC_022) |
| INV-030-02 | Soma das `qty_pct` dos TP parciais <= 100 | D-006 |
| INV-030-03 | `activation_threshold` > `trail_distance` | D-006 |
| INV-030-04 | TP parcial só reduz posição — nunca aumenta | D-001 |
| INV-030-05 | NENHUMA lógica de pós-processamento após abertura | D-001 |
| INV-030-06 | Config inválida (D-006) causa erro fatal no startup, não warning | D-006 |
| INV-030-07 | Se `exit_strategy="fixed"`: comportamento atual inalterado | D-003 |
| INV-030-08 | Número de níveis TP: `1 <= len(tp_levels) <= 3` | D-006 (G-003) |

---

## 7. Testes

| ID | Descrição | Responsável |
|----|-----------|-------------|
| TEST_030_01 | TP parcial com 2 níveis: TP1 executa → posição reduz → SL permanece | Time B |
| TEST_030_02 | TP parcial com 3 níveis: TP1+TP2+TP3 executam sequencialmente | Time B |
| TEST_030_03 | Exit strategy = "fixed" → comportamento atual (sem TP parcial) | Time B |
| TEST_030_04 | SL original nunca é movido ou cancelado após TP parcial (DD-002) | Time B |
| TEST_030_05 | SimulatedBinanceClient executa TP parcial corretamente | Time B |
| TEST_030_06 | Config validation rejeita `sum(qty_pct) > 100` com erro fatal | Time B |
| TEST_030_07 | Config validation rejeita `len(tp_levels) < 1` ou `len(tp_levels) > 3` | Time B |
| TEST_030_08 | Config validation rejeita `qty_pct <= 0` ou `pct <= 0` | Time B |
| TEST_030_09 | RRR médio ponderado calculado corretamente com 2+ níveis | Time B |

---

## 8. Arquivos

| Arquivo | Mudança | Prioridade |
|---------|---------|-----------|
| `src/config/settings.py` | Adicionar `EXIT_STRATEGY`, `TP_LEVELS` + config validation no startup | V1 |
| `src/trading/order_manager.py` | Modificar `execute()` — enviar TP levels + SL como reduceOnly se `exit_strategy="partial"` | V1 |
| `src/trading/order_manager.py` | Adicionar campos `exit_strategy`, `tp_levels` ao modelo `Trade` | V1 |
| `src/trading/position_model.py` | Atualizar schema e documentação | V1 |
| `src/exchange/binance_client.py` | Garantir que `create_take_profit_order` aceita `reduceOnly` | V1 |
| `src/exchange/simulated_client.py` | Suporte a N ordens reduceOnly simultâneas | V1 |
| `src/main.py` | Passar `exit_strategy` e `tp_levels` para OrderManager | V1 |
| `tests/trading/test_exit_strategies.py` | TEST_030_01 a 09 | V1 |
| `src/exchange/binance_client.py` | `create_trailing_stop_order()` via `POST /fapi/v1/algo` | V2 |
| `src/config/settings.py` | `TRAILING_ACTIVATION_PCT`, `TRAILING_CALLBACK_RATE` | V2 |

---

## 9. Definition of Done

- [ ] TP parcial com até 3 níveis configuráveis, ordens reduceOnly nativas (D-001)
- [ ] SL original nunca reenviado ou movido pós-TP1 (D-004)
- [ ] Algoritmo genérico para N níveis (G-001)
- [ ] SimulatedBinanceClient suporta N ordens reduceOnly (RF-030-07)
- [ ] Config validation fatal no startup cobre `len >= 1`, `qty_pct > 0`, `sum <= 100` (D-006, G-003)
- [ ] RRR médio ponderado para trades com saída parcial (D-007)
- [ ] Logging de execução de saída: nível, preço, quantidade remanescente, condições de mercado (D-008)
- [ ] Modo legado `"fixed"` mantém comportamento atual (D-003)
- [ ] TEST_030_01 a 09 passando
- [ ] `ruff check src/ tests/` limpo
- [ ] V2: Verificação técnica concluída (ccxt + Testnet)
- [ ] V2: TRAILING_STOP_MARKET funcional via Algo Order API (quando aplicável)

---

## 10. Decisões de Arquitetura (ADR)

As decisões abaixo foram tomadas durante o refinamento (ver `refinamento-2026-05-11.md` para detalhes):

| ID | Decisão | Resumo |
|----|---------|--------|
| D-001 | TP parcial via ordens reduceOnly nativas | SL/TPs enviados juntos na abertura. Exchange gerencia. Zero pós-processamento. |
| D-002 | Trailing via TRAILING_STOP_MARKET nativo | Algo Order API. Chamada REST direta. callbackRate fixo. |
| D-003 | Modo `"fixed"` como default | Migração opt-in por símbolo. |
| D-004 | **Rejeitado** reenvio de SL pós-TP1 | Desnecessário com reduceOnly. Arriscado. |
| D-005 | **Rejeitado** trailing adaptativo | callbackRate fixo. Adaptativo exigiria cancelar/recriar ordens. |
| D-006 | Config validation fatal no startup | Padrão SPEC_022. Erro fatal, não warning. |
| D-007 | RRR médio ponderado | Média ponderada pela qty de cada nível. |
| D-008 | Logging de execução de saída | Nível, preço, qty remanescente, condições de mercado. |
