# Artefatos da Sessão — SPEC_030 Saída Dinâmica

**Data:** 2026-05-11
**Sessão:** Time A (Refinamento) — Facilitador Externo + Tech Lead
**Status:** Decisões Parciais — aguardando encerramento formal

---

## Objetivo

Refinar o rascunho v1.0 da SPEC_030 (Saída Dinâmica: Trailing Stop e Take-Profit Parcial) à luz de pareceres técnicos da Binance Futures API, eliminando riscos operacionais e divergências entre membros do Time A.

---

## Especialistas Participantes

| Membro | Papel |
|--------|-------|
| Trader Sênior | Âncora da estratégia — guardião do método Phicube |
| Product Owner | Guardião do escopo e valor de negócio |
| Risk Manager | Guardião do capital — riscos financeiros e operacionais |
| Quant Developer | Rigor analítico — viabilidade matemática e técnica |
| ML/AI Engineer | Visão de futuro — oportunidades inteligentes |
| Backend Sênior | Parecer técnico — Binance Futures API (consultado) |

---

## Decisões Tomadas

### D-001: TP Parcial via ordens reduceOnly nativas (V1)
**Decisão:** TP parcial é implementado enviando TP1, TP2 e SL como ordens `reduceOnly=true` na abertura da posição. NENHUMA lógica de pós-processamento é necessária — a exchange Binance ajusta automaticamente as ordens reduceOnly remanescentes quando a posição reduz.
- ✅ SL original permanece intocado — DD-002 respeitado
- ✅ Zero timing risk entre TP1 e reenvio de SL
- ✅ Zero linhas de código para gerenciamento de estado pós-parcial
- **Responsável Time B:** Backend Sênior + Quant Developer

### D-002: Trailing Stop via TRAILING_STOP_MARKET nativo (V2)
**Decisão:** Trailing stop será implementado usando o tipo de ordem `TRAILING_STOP_MARKET` da Binance Futures (Algo Order API), com parâmetros `activatePrice` e `callbackRate`. A abordagem de TAKE_PROFIT_LIMIT móvel (do rascunho original) é **rejeitada** por risco de não execução em gaps de mercado.
- Chamada direta ao endpoint `POST /fapi/v1/algo` (não via ccxt)
- callbackRate fixo configurável por símbolo (não adaptativo)
- **Responsável Time B:** Backend Sênior

### D-003: Modo legacy mantido como default
**Decisão:** `exit_strategy = "fixed"` permanece como configuração padrão. A migração para saída dinâmica é opt-in por símbolo via `.env`.
- `"fixed"` — comportamento atual (SL + TP fixos)
- `"partial"` — TP parcial com N níveis (V1)
- `"trailing"` — trailing stop nativo (V2, futuro)
- `"partial+trailing"` — combinado (futuro)

### D-004: Rejeitado — ajuste de SL pós-TP1 (proposta original)
**Decisão:** O rascunho original previa reenviar SL para break-even após TP1. Com ordens reduceOnly nativas, isso é desnecessário e arriscado. Removido do escopo.

### D-005: Rejeitado — trailing adaptativo por ATR
**Decisão:** O `callbackRate` do TRAILING_STOP_MARKET é fixo no momento da criação. Fazer trailing adaptativo exigiria cancelar e recriar ordens, introduzindo latência e risco. Descartado para esta SPEC. Mantido como hipótese documentada para ciclo futuro.

### D-006: Config validation no startup (padrão SPEC_022)
**Decisão:** Validar configurações da estratégia de saída na inicialização, mesmo padrão do `LEVERAGE <= 20x`:
- Se `exit_strategy` contém "partial": `sum(lvl.qty_pct) <= 100`
- Se `exit_strategy` contém "trailing": `activation_threshold > trail_distance`
- Erro fatal no startup (não warning)

### D-007: RRR médio ponderado para trades com saída parcial
**Decisão:** Para trades com TP parcial, o RRR realizado é calculado como média ponderada pela quantidade de cada nível. Ex.: TP1 50% @ 2% (RRR=2.0) + TP2 50% @ 4% (RRR=4.0) → RRR médio = 3.0.

---

## Requisitos Levantados

### Funcionais

| ID | Requisito | Prioridade |
|----|-----------|------------|
| RF-030-01 | TP parcial com até 3 níveis configuráveis, ordens reduceOnly nativas | Alta |
| RF-030-02 | Estratégia de saída configurável por símbolo com fallback global | Alta |
| RF-030-03 | Modo legacy (`fixed`) mantém comportamento atual | Alta |
| RF-030-04 | TRAILING_STOP_MARKET nativo via Algo Order API | Média (V2) |
| RF-030-05 | Logging de ativação e execução de saída | Alta |
| RF-030-06 | Logging de condições de mercado no momento da saída (volatilidade, spread, volume) | Média |

### Não-Funcionais

| ID | Requisito | Prioridade |
|----|-----------|------------|
| RNF-030-01 | Config validation no startup com erro fatal | Alta |
| RNF-030-02 | Intervenção zero do bot no SL original (DD-002) | Alta |
| RNF-030-03 | Compatibilidade com modo simulation (SimulatedBinanceClient) | Alta |

---

## Pareceres Técnicos Consultados

- **@backend-senior** → Confirmou que ordens reduceOnly se ajustam automaticamente com redução de posição na Binance Futures (One-way Mode). Confirmou suporte nativo a `TRAILING_STOP_MARKET` via Algo Order API (`POST /fapi/v1/algo`). Alertou sobre migração de ordens condicionais para Algo Order API (impacto no código atual via ccxt).

---

## Hipóteses a Validar

| ID | Hipótese | Como Testar | Prazo |
|----|----------|-------------|-------|
| H-001 | Ordens reduceOnly múltiplas (TP1 + TP2 + SL) funcionam simultaneamente em One-way Mode na Testnet | Criar posição em Testnet com 3 ordens reduceOnly e verificar comportamento ao executar TP1 | V1 |
| H-002 | ccxt versão atual suporta TRAILING_STOP_MARKET ou precisamos de chamada direta ao Algo Order API | `python -c "import ccxt; print(ccxt.__version__)"` + teste em Testnet | V2 |
| H-003 | O Algo Order API está disponível e estável na Testnet | Chamada `POST /fapi/v1/algo` com TRAILING_STOP_MARKET em Testnet | V2 |

---

## Riscos Identificados

| ID | Risco | Impacto | Mitigação |
|----|-------|---------|-----------|
| R-001 | ccxt versão desatualizada não suporta Algo Order API | Alto — V2 bloqueada | Usar chamada REST direta ao `/fapi/v1/algo` |
| R-002 | Testnet não suporta TRAILING_STOP_MARKET | Médio — V2 não testável em Testnet | Validar na documentação; se não suportar, aceitar risco em produção |
| R-003 | Config complexa confunde operador (5 modos de saída) | Baixo | Default = "fixed" (comportamento conhecido); documentação clara |

---

## Questões em Aberto

- Nenhuma. Todas as decisões foram tomadas nesta sessão.

---

## Direcionamento para o Time B (Execução)

### Prioridade 1 — TP Parcial (V1)

**Arquivos e mudanças:**

| Arquivo | Mudança |
|---------|---------|
| `src/config/settings.py` | Adicionar `EXIT_STRATEGY`, `TP_LEVELS` + config validation no startup |
| `src/trading/order_manager.py` | Modificar `execute()` para enviar TP1, TP2, SL como reduceOnly se `exit_strategy="partial"` |
| `src/trading/order_manager.py` | Adicionar campo `exit_strategy` e `tp_levels` ao modelo `Trade` |
| `src/trading/position_model.py` | Atualizar schema/documentação |
| `src/exchange/binance_client.py` | Verificar se `create_take_profit_order` aceita `reduceOnly` corretamente |
| `src/main.py` | Passar `exit_strategy` e `tp_levels` para OrderManager |
| `tests/trading/test_exit_strategies.py` | TEST_030_01 a 06 (criar) |

**Algoritmo (definitivo):**
```
Na abertura (execute()):
  1. Calcular SL fixo (fractal — como hoje)
  2. Calcular qty_tp1 = total_qty * tp_levels[0].qty_pct / 100
  3. Calcular qty_tp2 = total_qty * tp_levels[1].qty_pct / 100
  4. Enviar ordem MARKET de entrada (como hoje)
  5. Enviar STOP_MARKET (SL) com reduceOnly=true, qty = total_qty
  6. Enviar TAKE_PROFIT_MARKET (TP1) com reduceOnly=true, qty = qty_tp1
  7. Enviar TAKE_PROFIT_MARKET (TP2) com reduceOnly=true, qty = qty_tp2
  ⚠️ NENHUMA lógica de pós-processamento
  🔒 DD-002 respeitado: SL original permanece
```

**Config:**
```python
EXIT_STRATEGY: str = "fixed"  # "fixed" | "partial" | "trailing" | "partial+trailing"
TP_LEVELS: list[dict] = [
    {"pct": 2.0, "qty_pct": 50},
    {"pct": 4.0, "qty_pct": 50},
]
```

### Prioridade 2 — Verificação Técnica (pré-V2)

- [ ] Verificar versão da ccxt: `python -c "import ccxt; print(ccxt.__version__)"`
- [ ] Testar em Testnet se `create_stop_loss_order` e `create_take_profit_order` atuais funcionam
- [ ] Testar em Testnet se TRAILING_STOP_MARKET é suportado via Algo Order API
- [ ] Relatar resultado — se viável, implementar V2 no mesmo ciclo

### Prioridade 3 — Trailing Stop Nativo (V2, condicional à verificação acima)

- [ ] Adicionar `TRAILING_ACTIVATION_PCT` e `TRAILING_DISTANCE_PCT` em settings.py
- [ ] Criar `BinanceClient.create_trailing_stop_order()` via chamada direta ao Algo Order API
- [ ] Adicionar lógica em `OrderManager` para modo `"trailing"`

### Skills de Validação Recomendadas

- **@qa-review** — para validar cobertura de testes (TEST_030_01 a 06)
- **@signal-review** — não aplicável (mudança é na saída, não na entrada)
- **@security-audit** — verificar se chamada ao Algo Order API expõe credenciais em logs
