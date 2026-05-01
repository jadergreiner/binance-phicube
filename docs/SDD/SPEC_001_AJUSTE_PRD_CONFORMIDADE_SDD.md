# SPEC 001 — Ajuste do PRD para Conformidade SDD

**ID:** SPEC_001  
**Status:** Aprovada pelo Time A  
**Data:** 2026-05-01  
**Autor:** Time A (Refinamento)  
**Executores:** Time B (Execução)  
**Skill de validação:** `sdd-spec-driven-development`, `qa-review`

---

## 1. Objetivo

Formalizar a conformidade do `PRD.md` com o modelo SDD, garantindo que cada requisito de produto possua:

- Rastreabilidade explícita para a seção técnica correspondente em `docs/SDD/SPEC.md`
- Critério de aceite mensurável e testável
- Invariante ou contrato técnico verificável

Ao final desta SPEC, o Time B terá base objetiva para implementação e validação sem necessidade de interpretação subjetiva.

## 2. Escopo

### Em escopo

- [x] Formalizar critérios de aceite de todos os requisitos funcionais do MVP (PRD § Escopo Detalhado)
- [x] Definir invariantes técnicas para risco e execução de ordens
- [x] Mapear rastreabilidade PRD → SPEC.md → testes
- [x] Definir comportamento esperado em cenários de erro críticos

### Fora de escopo

- [ ] Fase 2 do PRD (dashboard, backtests, alertas, múltiplas estratégias)
- [ ] Refatoração arquitetural além do necessário para conformidade
- [ ] Infraestrutura de CI/CD (tratado em SPEC futura)

## 3. Rastreabilidade com PRD

| Requisito PRD | Seção PRD | Seção SPEC.md | Seção desta SPEC | Critério de Teste |
|---|---|---|---|---|
| Detecção de sinal LONG/SHORT | MVP § 1 | SPEC.md § 2.1 | 4.1 | `TEST_001_01` |
| Cálculo de posição com risco controlado | MVP § 2 | SPEC.md § 2.2 | 4.2 | `TEST_001_02` |
| Execução atômica com rollback | MVP § 3 | SPEC.md § 2.3 | 4.3 | `TEST_001_03` |
| Logging estruturado de toda operação | MVP § 4 | SPEC.md § 2.6 | 4.4 | `TEST_001_04` |
| Resiliência: sem ordem duplicada | MVP § 5 | SPEC.md § 2.4 | 4.5 | `TEST_001_05` |
| Limite de risco por operação | Critérios de Sucesso | SPEC.md § 2.2 | 5.2 | `TEST_001_06` |
| Segurança: chave nunca em código | Restrições de Segurança | SPEC.md § 2.6 | 4.4 | `TEST_001_07` |

## 4. Especificação Funcional

### 4.1 Regra 1 — Detecção de Sinal (`TEST_001_01`)

**Descrição:** o sistema deve detectar sinais LONG e SHORT válidos com base em Alligator + AO + Fractais de 5 barras, avaliando exclusivamente candles já fechados.

**Entradas:**

- `symbol`: par cripto (ex.: `BTCUSDT`)
- `timeframe`: intervalo de candle (ex.: `4h`)
- `df`: DataFrame OHLCV com mínimo 200 candles, sem o candle atual em progresso

**Pré-condições:**

- `df.shape[0] >= 200` (warmup mínimo)
- Colunas presentes: `open`, `high`, `low`, `close`, `volume`

**Fluxo esperado:**

1. Computar indicadores: Alligator (jaw, teeth, lips), AO e Fractais
2. Verificar alinhamento do Alligator na última candle fechada
3. Verificar sinal do AO na última candle fechada
4. Localizar fractal válido nos últimos 100 candles (excluindo as 2 últimas barras)
5. Calcular `entry_price`, `stop_loss` e `take_profit`
6. Retornar `Signal` ou `None`

**Saída esperada:**

- `Signal(symbol, timeframe, direction, entry_price, stop_loss, take_profit, fractal_ref, detected_at)`
- `None` se nenhuma das condições for satisfeita

**Critério de aceite (PRD ≥ 95% de acurácia):**

- Validação manual contra 20+ setups históricos conhecidos: todos devem ser detectados ou rejeitados corretamente

---

### 4.2 Regra 2 — Cálculo de Posição com Risco Controlado (`TEST_001_02`)

**Descrição:** o sistema deve calcular o tamanho de posição proporcional ao risco configurado, respeitando limites máximos por símbolo e total de posições abertas.

**Entradas:**

- `signal`: sinal válido com `entry_price` e `stop_loss`
- `available_balance`: saldo USDT disponível
- `quantity_precision`: casas decimais permitidas pela exchange

**Pré-condições:**

- `signal.stop_loss != signal.entry_price` (stop_distance > 0)
- `count_open_positions() < max_open_positions`

**Fluxo esperado:**

1. `risk_amount = available_balance * (risk_per_trade_pct / 100)`
2. `stop_distance = abs(entry_price - stop_loss)`
3. `qty_base = risk_amount / stop_distance`
4. `margin_required = (entry_price * qty_base) / leverage`
5. Se `margin_required > balance * max_capital_allocation_pct / 100`: aplicar scale-down
6. `qty = round(qty_base, quantity_precision)`
7. Validar `qty > 0` e `RRR >= risk_reward_ratio`

**Saída esperada:**

- `PositionSize(quantity, risk, reward, risk_reward_ratio, margin_used)` ou `None`

---

### 4.3 Regra 3 — Execução Atômica com Rollback (`TEST_001_03`)

**Descrição:** o sistema deve executar entrada → SL → TP como operação atômica: se qualquer ordem falhar após a entrada ser executada, cancelar todas e registrar falha.

**Entradas:**

- `signal`: sinal com `entry_price`, `stop_loss`, `take_profit`
- `position`: `PositionSize` com `quantity`

**Pré-condições:**

- Leverage configurado antes da ordem de entrada
- Margin mode configurado antes da ordem de entrada

**Fluxo esperado:**

1. `set_leverage(symbol, leverage)` — se falha: retornar `None`
2. `set_margin_mode(symbol, "isolated")` — se falha: retornar `None`
3. `create_market_order(...)` — se falha: retornar `None`
4. `create_stop_loss_order(reduceOnly=True)` — se falha: `cancel_all_orders()`, status `FAILED`
5. `create_take_profit_order(reduceOnly=True)` — se falha: `cancel_all_orders()`, status `FAILED`
6. Retornar `Trade(status=ACTIVE)` com IDs de todas as ordens

**Saída esperada:**

- `Trade(entry_order_id, stop_loss_order_id, take_profit_order_id, status=ACTIVE)`
- `Trade(status=FAILED)` se qualquer ordem posterior falhar, com rollback executado

---

### 4.4 Regra 4 — Logging Estruturado Obrigatório (`TEST_001_04`)

**Descrição:** o sistema deve emitir log estruturado (JSON em produção, console em dev) para cada evento operacional relevante, sem expor credenciais.

**Eventos obrigatórios:**

| Evento | Nível | Campos mínimos |
|---|---|---|
| `signal_detected` | INFO | symbol, direction, entry, sl, tp |
| `position_calculated` | INFO | symbol, qty, risk, reward, rrr |
| `order_entry_executed` | INFO | symbol, entry_order_id, price |
| `order_sl_executed` | INFO | symbol, sl_order_id, price |
| `order_tp_executed` | INFO | symbol, tp_order_id, price |
| `order_failed` | ERROR | symbol, reason |
| `api_retry` | WARNING | endpoint, attempt, next_wait_ms |
| `record_saved` | INFO | collection, count |

**Invariante de segurança:**

- `api_key`, `api_secret`, senhas MongoDB e tokens nunca devem aparecer em nenhum log

---

### 4.5 Regra 5 — Resiliência e Prevenção de Duplicação (`TEST_001_05`)

**Descrição:** o sistema deve sobreviver a reinicializações e falhas de rede sem criar ordens duplicadas e sem deixar posições sem proteção.

**Mecanismos obrigatórios:**

- `entry_order_id` como índice único no MongoDB (rejeita duplicata)
- Retry com backoff exponencial (1s, 2s, 4s) para erros recuperáveis
- Verificação de `count_open_positions()` antes de nova ordem
- Verificação de símbolo já em trade aberto antes de nova ordem

**Critério de aceite (PRD ≥ 48h contínuas):**

- Nenhuma posição aberta fica sem SL após reinicialização do bot
- Nenhuma ordem duplicada criada após reconexão

---

## 5. Contrato Técnico

### 5.1 Interface Principal

```python
# Signal Engine
class SignalEngine:
    def evaluate(
        self,
        symbol: str,
        timeframe: str,
        df: pd.DataFrame
    ) -> Signal | None: ...

# Risk Manager
class RiskManager:
    def calculate(
        self,
        signal: Signal,
        available_balance: float,
        quantity_precision: int = 3
    ) -> PositionSize | None: ...

# Order Manager
class OrderManager:
    async def execute(
        self,
        signal: Signal,
        position: PositionSize
    ) -> Trade | None: ...
```

### 5.2 Invariantes (não podem ser violadas)

- [ ] `signal.stop_loss < signal.entry_price` para LONG
- [ ] `signal.stop_loss > signal.entry_price` para SHORT
- [ ] `signal.risk_reward_ratio >= config.risk_reward_ratio` (padrão: 2.0)
- [ ] `position.risk == available_balance * risk_per_trade_pct / 100`
- [ ] `margin_used <= available_balance * max_capital_allocation_pct / 100`
- [ ] `count_open_positions() < max_open_positions` antes de qualquer nova entrada
- [ ] SL e TP sempre `reduceOnly=True`
- [ ] `entry_order_id` único em toda a base de dados

### 5.3 Erros e Exceções

| Cenário | Erro esperado | Comportamento |
|---|---|---|
| Rate limit Binance (429) | `ccxt.RateLimitExceeded` | Retry × 3 com backoff exponencial |
| Timeout de rede | `asyncio.TimeoutError` | Retry × 3 com backoff exponencial |
| Chave inválida (401) | `ccxt.AuthenticationError` | Falha fatal, log ERROR, parar bot |
| Saldo insuficiente | `ccxt.InsufficientFunds` | Retornar `None`, log WARNING |
| SL falha após entrada | `ccxt.*Error` | `cancel_all_orders()`, `Trade(status=FAILED)` |
| Inserção duplicada MongoDB | `DuplicateKeyError` | Log WARNING, ignorar silenciosamente |
| DataFrame muito curto | `ValueError` | Retornar `None`, log WARNING |

## 6. Critérios de Aceite

Derivados diretamente dos critérios de sucesso do PRD:

- [ ] `TEST_001_01`: ≥ 95% de acurácia na detecção de sinal validada contra 20+ setups históricos
- [ ] `TEST_001_02`: 0 violações de limite de risco em 50 cenários de posição (variando saldo, SL, leverage)
- [ ] `TEST_001_03`: 100% de success rate em 50 execuções no Testnet (entrada + SL + TP)
- [ ] `TEST_001_04`: 100% das operações com log completo e rastreável; 0 credenciais em logs
- [ ] `TEST_001_05`: 0 ordens duplicadas em 10 reinicializações simuladas; 0 posições sem SL após reinício
- [ ] `TEST_001_06`: Latência sinal → execução ≤ 2 segundos (medição com timestamps nos logs)
- [ ] `TEST_001_07`: `git ls-files | grep -i api_key` retorna vazio; `pip-audit` sem CVE crítico

## 7. Testes de Conformidade

### 7.1 Testes Unitários

- [ ] `test_signal_long_valid`: sinal LONG detectado com Alligator bullish + AO>0 + fractal bullish
- [ ] `test_signal_short_valid`: sinal SHORT detectado com Alligator bearish + AO<0 + fractal bearish
- [ ] `test_signal_none_alligator_not_aligned`: retorna `None` quando Alligator não alinhado
- [ ] `test_signal_none_ao_zero`: retorna `None` quando AO = 0
- [ ] `test_signal_none_no_fractal`: retorna `None` sem fractal válido nos últimos 100 candles
- [ ] `test_position_risk_exact`: risk_amount == balance × risk_pct com precisão float
- [ ] `test_position_scale_down`: qty reduzida quando margin > max_capital_allocation
- [ ] `test_position_none_max_positions`: retorna `None` quando max_open_positions atingido
- [ ] `test_position_rrr_minimum`: retorna `None` quando RRR calculado < config.risk_reward_ratio
- [ ] `test_trade_rollback_sl_failure`: `cancel_all_orders` chamado se SL falha
- [ ] `test_trade_rollback_tp_failure`: `cancel_all_orders` chamado se TP falha
- [ ] `test_duplicate_key_ignored`: segunda inserção com mesmo `entry_order_id` não gera exceção

### 7.2 Testes de Integração (Testnet)

- [ ] `test_full_long_cycle_testnet`: sinal LONG → posição → entrada → SL → TP, todos com IDs reais
- [ ] `test_full_short_cycle_testnet`: sinal SHORT → ciclo completo
- [ ] `test_reconnect_no_duplicate`: simular queda e reconexão; verificar 0 duplicação de ordem
- [ ] `test_48h_stability`: bot roda 48h no Testnet sem crash ou memory leak

### 7.3 Evidências Obrigatórias na PR

- [ ] Output de `pytest -v --cov=src --cov-report=term-missing` colado ou anexado
- [ ] Log de ao menos 1 ciclo completo (sinal detectado → trade ativo) do Testnet
- [ ] Referência às seções de `SPEC.md` e `SPEC_001` impactadas no corpo da PR

## 8. Riscos e Mitigações

| Risco | Impacto | Mitigação |
|---|---|---|
| Sinal detectado na candle em progresso | Alto | `df` deve descartar último candle antes de `evaluate()` |
| SL não executado após entrada | Alto — perda ilimitada | Rollback obrigatório + alerta `order_failed` |
| Posição sem proteção após reinicialização | Alto | Verificação de posições abertas no startup |
| Credencial vazando em log | Alto — perda financeira | Revisão de log em `security-audit` antes de produção |
| RRR abaixo do mínimo aceito | Médio | Invariante verificada antes de executar ordem |
| DataFrame curto gerando cálculo inválido | Médio | Validação de `df.shape[0] >= 200` com retorno `None` |

## 9. Definição de Pronto (DoD)

- [x] SPEC_001 preenchida e aprovada pelo Time A
- [ ] Implementação aderente a todos os contratos desta SPEC
- [ ] `pytest` com 100% das asserções críticas passando
- [ ] Rastreabilidade PRD → SPEC.md → SPEC_001 → Teste → Código comprovada na PR
- [ ] Nenhuma invariante da seção 5.2 violada em nenhum cenário de teste

## 10. Plano de Entrega

1. **Time B lê** `docs/SDD/SPEC.md` (seções 2.1–2.6) + esta SPEC_001
2. **Time B implementa** componente a componente na ordem: Signal Engine → Risk Manager → Order Manager → Exchange → Storage → Logger
3. **Time B valida** cada componente com `qa-review` e `signal-review`
4. **PR criada** com evidências da seção 7.3
5. **Time A revisa** conformidade antes do merge

---

## Histórico

- **2026-05-01:** Criação do template SPEC_001.
- **2026-05-01:** Preenchido pelo Time A após sessão de refinamento sobre conformidade SDD do PRD.

## 10. Plano de Entrega

1. Refinar lacunas desta SPEC com Time A
2. Implementar no Time B por componente afetado
3. Validar com `qa-review` e, se aplicável, `signal-review`/`security-audit`
4. Liberar somente após conformidade completa

---

## Histórico

- **2026-05-01:** Criação da SPEC_001 no padrão SDD.
