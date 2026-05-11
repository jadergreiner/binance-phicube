# PRD — Position Sizing por ATR

**Vinculado a:** SPEC_029 — Position Sizing por ATR
**PRD Principal:** [`PRD.md`](../../PRD.md)
**Data:** 2026-05-11
**Versão:** 1.0
**Status:** Refinado (Aguardando Time B)

---

## 1. Sumário Executivo

Hoje o bot calcula o tamanho da posição como **percentual fixo do saldo** (`risk_per_trade_pct`). Isso funciona quando todos os pares têm volatilidade similar. Mas o portfólio atual tem **29 símbolos** com volatilidades que variam de ~5 USDT (BROCCOLI714) a ~500 USDT (BTCUSDT) de ATR. Um mesmo percentual de risco produz posições desproporcionais — trades inviáveis em pares voláteis (posição arredonda para zero) e risco excessivo em pares calmos (stop_distance pequeno → posição grande).

**Position Sizing por ATR resolve isso:** cada trade arrisca um valor FIXO em USDT, independente do par. O ATR ajusta o tamanho da posição conforme a volatilidade real do ativo.

---

## 2. Problema que Resolve

| Problema | Impacto Hoje | Como ATR Resolve |
|----------|-------------|------------------|
| **Trades inviáveis em pares voláteis** | BTCUSDT com stop de $500 → posição de 0.006 BTC → arredonda para 0. Trade nunca abre | ATR reduz posição automaticamente em ativos voláteis; risco em USDT permanece o mesmo |
| **Risco descalibrado entre pares** | BROCCOLI714 com stop de $5 → posição 3x maior que BTC para o mesmo risco % | `effective_stop = max(fractal, ATR * mult)` normaliza o risco real entre pares |
| **Operador não sabe quanto vai perder** | `risk_per_trade_pct` = 1% de $300 = $3, mas risco REAL depende da distância do SL | `RISK_PER_TRADE_USDT` = $5 → operador sabe exatamente: "nunca perco mais que $5 neste trade" |
| **Superdimensionamento oculto** | ATR baixo + fractal distante → posição grande + SL longe → risco real explode | `max(fractal_distance, ATR * multiplier)` nunca deixa effective_stop menor que o ATR |

### Cenário Ilustrativo (com dados reais do portfólio)

| Par | ATR (14) | Stop Fractal | Sizing % Hoje | Sizing ATR | Risco Real (Hoje) | Risco Real (ATR) |
|-----|----------|-------------|---------------|------------|-------------------|------------------|
| BTCUSDT | ~500 | ~400 | ~$3 (0.006 BTC) | ~$5 (0.01 BTC) | Posição = 0 (inviável) | $5 (trade viável) |
| BROCCOLI714USDT | ~5 | ~8 | ~$20 (4 uni) | ~$5 (1 uni) | Risco real ~$6 | Risco real ~$5 |
| QNTUSDT | ~15 | ~20 | ~$5 (2 uni) | ~$5 (2 uni) | Risco real ~$5 | Risco real ~$5 |

---

## 3. Valor para o Operador

1. **Previsibilidade de risco:** o operador sabe exatamente quantos USDT está arriscando por trade (`RISK_PER_TRADE_USDT`)
2. **Portfólio equilibrado:** todos os 29 pares competem com o mesmo critério de risco — não há "ativos que nunca abrem trade" por serem voláteis demais
3. **Proteção contra volatilidade:** em mercados agitados (ATR alto), o sistema automaticamente reduz posição — sem o operador precisar ajustar nada
4. **Transparência:** cada cálculo de posição loga `effective_stop`, `atr_value`, `fractal_sl_distance` — auditável a qualquer momento

---

## 4. Critérios de Sucesso

| Critério | Métrica | Alvo | Como Verificar |
|----------|---------|------|----------------|
| **Risco previsível** | Variação do risco real entre pares | ≤ 10% do `RISK_PER_TRADE_USDT` | Simulação 5 pares com 30 dias de OHLCV |
| **Zero trades inviáveis** | Trades rejeitados por `quantity_zero_after_rounding` | 0 após ativação do ATR | Dashboard + logs |
| **Invariante de risco** | `position_usdt * (effective_stop / entry_price)` | ≤ `RISK_PER_TRADE_USDT * 1.05` | TEST_029_08 (100 cenários) |
| **Adoção** | Trades executados em modo ATR vs. fixed | 100% dos novos trades em ATR após rollout | MongoDB `trades.sizing_mode` |

---

## 5. Decisões de Produto

### Tomadas nesta sessão

| Decisão | Opção Escolhida | Alternativa Rejeitada | Motivo |
|---------|----------------|----------------------|--------|
| Modo de sizing | `atr_with_guard` (`max(fractal, ATR)`) | `atr_simple` (só ATR) | Risco de superdimensionamento no `atr_simple` é inaceitável (Princípio 2 do Manifesto) |
| Risco configurável | `RISK_PER_TRADE_USDT` (USDT fixo) | Manter `risk_per_trade_pct` (%) | Previsibilidade: operador sabe exatamente o risco em USDT |
| Default `RISK_PER_TRADE_USDT` | 5.0 | Valor maior (10, 20) | Saldo inicial de $300; 5 USDT = 1.6% do saldo |
| Timeframe do ATR | Mesmo timeframe do trade | Timeframe fixo (1h, 4h) | Coerência com o SL do fractal (mesma resolução) |
| Fallback | `atr` → `fixed` se NaN | Bloquear trade sem ATR | Disponibilidade: operação não pode parar por falta de dados |

### Em aberto (depende de simulação)

| Decisão | Responsável | Prazo |
|---------|-------------|-------|
| `atr_multiplier` final | Trader Sênior (homologa) | Após simulação 5 pares |
| `MIN_POSITION_USDT` vs. min notional Binance | Backend Sênior (validar) | Durante implementação |

---

## 6. Conformidade com o Manifesto

| Princípio | Como SPEC_029 atende |
|-----------|---------------------|
| 1. Disciplina | Regras de sizing são fixas e determinísticas — sem exceção |
| 2. Gestão de risco | `effective_stop = max(fractal, ATR)` garante que risco real NUNCA excede o configurado |
| 3. Transparência | `effective_stop` logado em todo cálculo de posição |
| 4. Configurabilidade | Operador configura `RISK_PER_TRADE_USDT`, `ATR_MULTIPLIER`, etc. |
| 5. Segurança | Sem impacto — não envolve credenciais |
| 6. Resiliência | Fallback para fixed se ATR indisponível — operação nunca para |
| 7. Evolução baseada em dados | Simulação de 5 pares calibra `atr_multiplier` antes de produção |

---

## 7. Risco e Rollout

### Estratégia de rollout

1. **Testes unitários** (8 cenários) — validam invariantes
2. **Simulação 5 pares** — calibra `atr_multiplier`
3. **Modo `fixed` como default** — `SIZING_MODE=fixed` preserva comportamento atual na atualização
4. **Operador ativa `atr` manualmente** via `.env` — sem surpresa
5. **Monitoramento pós-rollout** — acompanhar `effective_stop` logs e trades rejeitados

### Riscos conhecidos

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| `atr_multiplier` mal calibrado reduz oportunidades excessivamente | Média | Baixo (perde lucro, não capital) | Simulação prévia; reabrir Time A se > 3.0 |
| Quebra retroativa em trades abertos na migração | Baixa | Médio | `SIZING_MODE=fixed` como default; trades abertos mantêm cálculo original |
| Min notional não coberto por `MIN_POSITION_USDT=10` | Baixa | Médio | Validação durante implementação por par |

---

## 8. Fora de Escopo (v1)

- Sizing dinâmico com dados on-chain (volume, open interest)
- Kelly Criterion
- Redução progressiva de posição em drawdown
- Sizing automático por fração de equity
- ATR para definir SL (SL permanece no fractal — regra Phicube)

---

## 9. Conexão com PRD Principal

Este PRD_029 é uma **especificação de feature** que complementa o [`PRD.md`](../../PRD.md) principal:

- **PRD.md § Fase 2:** "Relatório automático periódico de performance via Telegram" → não afetado
- **PRD.md § Gestão de Risco:** `risk_per_trade_pct` → esta PRD adiciona o modo ATR como alternativa
- **PRD.md § Critério de Sucesso (Funcional):** nova métrica "Zero trades rejeitados por risco" adicionada
- **PRD.md § Riscos Conhecidos:** adicionar "Superdimensionamento em cenário ATR baixo + fractal distante" — mitigado pelo `atr_with_guard`

### Recomendação de atualização do PRD Principal

Após implementação e rollout, recomenda-se:

1. Adicionar `RISK_PER_TRADE_USDT` e `SIZING_MODE` à seção de Configuração User-facing do PRD.md
2. Adicionar métrica "Zero trades rejeitados por risco" aos Critérios de Sucesso
3. Adicionar risco "Superdimensionamento ATR/fractal" aos Riscos Conhecidos

---

## 10. Histórico

| Versão | Data | Autor | Mudanças |
|--------|------|-------|----------|
| 1.0 | 2026-05-11 | Time A (Refinamento) | Documento inicial pós-sessão de refinamento SPEC_029 |
