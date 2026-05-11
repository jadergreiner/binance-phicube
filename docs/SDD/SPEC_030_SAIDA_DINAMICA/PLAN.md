# PLAN — SPEC_030 Saída Dinâmica

**Versão:** 1.0
**Data:** 2026-05-11
**Baseado em:** PRD_030 (v1.0) · SPEC_030 (v2.0) · Análise de Patterns do Codebase

---

## 1. Resumo Executivo

Implementar saída dinâmica no bot Binance Phicube: **TP Parcial (V1)** como prioridade imediata, **Trailing Stop Nativo (V2)** condicional à verificação técnica da Algo Order API. A abordagem arquitetural segue o princípio D-001 (zero pós-processamento): todas as ordens de saída são emitidas na abertura da posição, e a exchange Binance gerencia o ajuste automático via ordens `reduceOnly`. Nenhum estado de posição é gerenciado pelo bot após a abertura.

---

## 2. Escopo

### In

- **V1 — TP Parcial (obrigatório):** Settings, Trade model, OrderManager.execute(), BinanceClient verification, SimulatedClient compat, main.py wiring, testes (9 cenários), `.env.example`
- **Verificação Técnica (pré-V2):** ccxt version check, Algo Order API test on Testnet
- **V2 — Trailing Stop (condicional):** BinanceClient.create_trailing_stop_order(), Settings fields, OrderManager trailing mode
- **Config validation:** Startup fatal error para configurações inválidas (D-006)

### Out

- Modo `"partial+trailing"` combinado (postergado)
- Re-entrada após TP parcial (SPEC futura)
- Trailing adaptativo por ATR (D-005 rejeitado)
- Frontend/UI de configuração

---

## 3. Padrões do Codebase (Patterns Identificados)

### P-001: Config por Pydantic + StrEnum + model_validator

SPEC_029 introduziu `SizingMode(StrEnum)` com valores `fixed`/`atr`. SPEC_030 segue o mesmo padrão:

```python
class ExitStrategy(StrEnum):
    FIXED = "fixed"
    PARTIAL = "partial"
    TRAILING = "trailing"  # V2 futuro
    # PARTIAL_TRAILING = "partial+trailing"  # postergado
```

Validação usa `@model_validator(mode="after")` — mesmo padrão de `validate_commodities_gate()` em `settings.py:277`.

### P-002: Criação de Ordem no BinanceClient

`create_stop_loss_order()` e `create_take_profit_order()` seguem template idêntico:
1. Montar `params` com `stopPrice` + `reduceOnly`
2. Chamar `self._exchange.create_order(symbol, type, side, amount, params)`
3. Log estruturado com order_id
4. Retornar dict da ordem

V2 deve criar `create_trailing_stop_order()` seguindo o mesmo template, mas chamando `POST /fapi/v1/algo`.

### P-003: Trade Dataclass + to_dict()

`Trade` em `order_manager.py:39` é dataclass com `to_dict()`. Novos campos seguem o padrão:
- Campo com type hint + default `None` para compatibilidade reversa
- `to_dict()` inclui o campo

### P-004: Rollback em falha de ordem

`execute()` usa três zonas com rollback:
1. Falha no entry → return None (sem ordem criada)
2. Falha no SL → cancel_all_orders + notificação SL_PROTECTION_FAILED → _failed_trade
3. Falha no TP → cancel_all_orders → _failed_trade

Para V1: se algum TP falha, **todas as ordens são canceladas** (rollback total, não parcial).

### P-005: Fixtures de Teste

`test_order_manager.py` usa `_sample_signal()`, `_sample_position()`, `_mock_client()` — padrão a ser seguido em `test_exit_strategies.py`.

### P-006: SimulatedClient espelha BinanceClient

`SimulatedBinanceClient` tem métodos com mesma assinatura de `BinanceClient`. Para V1, `create_take_profit_order()` já aceita múltiplas chamadas — o estado interno (`_orders`, `_positions`) já gerencia reduceOnly. Verificar se `_update_position()` lida com redução parcial (já faz via `reduce_ratio` em `create_market_order`: line 236).

### P-007: SymbolConfig Triplet Pattern

Config de símbolos usa `SYMBOL:TIMEFRAME:LEVERAGE`. A estratégia de saída poderia seguir o mesmo padrão: `SYMBOL:TIMEFRAME:LEVERAGE:EXIT_STRATEGY`, ou usar campo separado `exit_strategy_overrides: dict[str, str]`. Recomendação: campo separado (mais flexível para TP_LEVELS por símbolo).

### P-008: Config Sempre com Default Seguro

`SIZING_MODE=fixed` mantém comportamento atual como default. `EXIT_STRATEGY=fixed` segue mesmo princípio — operador opt-in.

---

## 4. Arquivos e Dependências

### V1 — TP Parcial

```
src/config/settings.py
  ├── Adicionar: ExitStrategy(StrEnum)
  ├── Adicionar: exit_strategy: ExitStrategy = ExitStrategy.FIXED
  ├── Adicionar: tp_levels: list[dict] = [{...}]  # default 2 níveis
  ├── Adicionar: exit_strategy_overrides: dict[str, str] = {}  # override por símbolo
  ├── Adicionar: @model_validator: validate_exit_strategy() (D-006)
  └── NOTA: Segue P-001, P-008

src/trading/order_manager.py
  ├── Trade: adicionar campos exit_strategy, tp_levels, tp_order_ids (P-003)
  ├── Trade.to_dict(): incluir novos campos
  ├── OrderManager.__init__(): aceitar exit_strategy, tp_levels
  ├── OrderManager.execute():
  │   ├── Se exit_strategy == "partial": loop de TAKE_PROFIT_MARKET (P-004)
  │   └── Se exit_strategy == "fixed": comportamento atual
  └── NOTA: SL permanece em total_qty. Exchange ajusta reduceOnly.

src/exchange/binance_client.py
  └── VERIFICAR: create_take_profit_order() aceita reduceOnly (já tem params["reduceOnly"]=True)
  └── NOTA: Nenhuma mudança necessária — API já suporta múltiplos TPs reduceOnly

src/exchange/simulated_client.py
  ├── create_take_profit_order(): já aceita múltiplas chamadas (P-006)
  ├── create_market_order() _update_position(): redução parcial já funciona
  └── NOTA: Criar método check_reduce_only_orders() para simular execução de TP

src/main.py
  ├── RuntimeMonitorRegistry._build_monitor(): passar exit_strategy, tp_levels ao OrderManager
  └── TradingMonitor._tick(): passar exit_strategy ao execute() — ou deixar OrderManager ler do config

tests/trading/test_exit_strategies.py (NOVO)
  ├── TEST_030_01: TP parcial 2 níveis → posição reduz, SL permanece
  ├── TEST_030_02: TP parcial 3 níveis → execução sequencial
  ├── TEST_030_03: exit_strategy="fixed" → comportamento atual
  ├── TEST_030_04: SL nunca movido (DD-002)
  ├── TEST_030_05: SimulatedClient executa TP parcial corretamente
  ├── TEST_030_06: Config validation rejeita sum > 100
  ├── TEST_030_07: Config validation rejeita len < 1 ou > 3
  ├── TEST_030_08: Config validation rejeita qty_pct <= 0
  ├── TEST_030_09: RRR médio ponderado
  └── Segue P-005: _sample_signal(), _mock_client()

.env.example
  └── Adicionar seção: "# Estratégia de Saída (SPEC_030)"
```

### Verificação Técnica (pré-V2)

```comandos
  python -c "import ccxt; print(ccxt.__version__)"  # H-002
  # Teste manual: criar TRAILING_STOP_MARKET via POST /fapi/v1/algo na Testnet (H-003)
```

### V2 — Trailing Stop (condicional)

```
src/config/settings.py
  ├── Adicionar: trailing_activation_pct: float = 1.0
  ├── Adicionar: trailing_callback_rate: float = 0.5
  └── Estender validate_exit_strategy(): activation_threshold > trail_distance

src/exchange/binance_client.py
  ├── NOVO: create_trailing_stop_order(symbol, side, qty, activatePrice, callbackRate)
  ├── Chamada REST direta: POST /fapi/v1/algo
  └── Segue P-002 (template de criação de ordem)

src/trading/order_manager.py
  └── execute(): se exit_strategy == "trailing", chama create_trailing_stop_order() no lugar do SL fixo
```

---

## 5. Ação por Ação

### Fase 1: Fundação — Settings + Validação

```
[ ] 1.1 Adicionar ExitStrategy enum em settings.py
[ ] 1.2 Adicionar campos: exit_strategy, tp_levels, exit_strategy_overrides
[ ] 1.3 Implementar @model_validator validate_exit_strategy() (D-006 + G-003)
[ ] 1.4 Adicionar logging de validação no startup
[ ] 1.5 Atualizar .env.example
```

📄 `src/config/settings.py` · `.env.example`

### Fase 2: Trade Model

```
[ ] 2.1 Adicionar campos exit_strategy, tp_levels, tp_order_ids ao Trade
[ ] 2.2 Atualizar Trade.to_dict()
[ ] 2.3 Garantir compatibilidade reversa (default None)
```

📄 `src/trading/order_manager.py` (Trade dataclass)

### Fase 3: SimulatedClient — Suporte TP Parcial

```
[ ] 3.1 Verificar create_market_order() já trata redução parcial (já faz!)
[ ] 3.2 Verificar create_take_profit_order() aceita múltiplas chamadas (já aceita!)
[ ] 3.3 Adicionar método check_and_execute_conditional_orders(symbol, current_price)
       - Percorre ordens abertas do símbolo
       - Se preço atingiu stopPrice de TP: executar ordem (reduzir posição)
       - Se preço atingiu stopPrice de SL: executar ordem (zerar posição)
  └── Este método permite que o modo simulation funcione sem polling externo
```

📄 `src/exchange/simulated_client.py`

### Fase 4: OrderManager — Lógica Central

```
[ ] 4.1 Modificar OrderManager.__init__() para aceitar exit_strategy, tp_levels
[ ] 4.2 Refatorar execute():
       [ ] 4.2.1 Extrair criação de SL para helper _create_sl_order()
       [ ] 4.2.2 Extrair criação de TP para helper _create_tp_orders()
       [ ] 4.2.3 Se exit_strategy="partial": criar N TAKE_PROFIT_MARKET orders
       [ ] 4.2.4 Se exit_strategy="fixed": comportamento atual
       [ ] 4.2.5 Rollback: se algum TP falha → cancel_all_orders (P-004)
       [ ] 4.2.6 Logging: cada TP criado loga nível, qty, price (D-008)
[ ] 4.3 Adicionar helper _calc_rrr_weighted() para D-007
[ ] 4.4 Trade retornado com exit_strategy e tp_levels populados
```

📄 `src/trading/order_manager.py`

### Fase 5: Main.py — Wiring

```
[ ] 5.1 RuntimeMonitorRegistry._build_monitor(): passar exit_strategy, tp_levels ao OrderManager
[ ] 5.2 TradingMonitor._tick(): exit_strategy disponível no OrderManager
[ ] 5.3 Garantir que settings.exit_strategy é lido na inicialização
```

📄 `src/main.py`

### Fase 6: Testes V1

```
[ ] 6.1 Criar tests/trading/test_exit_strategies.py
[ ] 6.2 Implementar TEST_030_01 a 09
[ ] 6.3 Executar: pytest tests/trading/test_exit_strategies.py -v --tb=short
[ ] 6.4 Executar: pytest tests/ -v --tb=short (garantir 0 regressão)
[ ] 6.5 Executar: ruff check src/ tests/
```

📄 `tests/trading/test_exit_strategies.py`

### Fase 7: Verificação Técnica (pré-V2)

```
[ ] 7.1 Verificar versão ccxt: python -c "import ccxt; print(ccxt.__version__)"
[ ] 7.2 Testar em Testnet se create_stop_loss_order + create_take_profit_order atuais funcionam
[ ] 7.3 Testar em Testnet: POST /fapi/v1/algo com TRAILING_STOP_MARKET
[ ] 7.4 Relatar resultado — se viável, implementar V2 no mesmo ciclo
```

### Fase 8: V2 — Trailing Stop (condicional)

```
[ ] 8.1 Adicionar trailing_activation_pct, trailing_callback_rate em settings.py
[ ] 8.2 Estender validate_exit_strategy() para modo "trailing"
[ ] 8.3 Implementar BinanceClient.create_trailing_stop_order()
       - Endpoint: POST /fapi/v1/algo
       - Parâmetros: symbol, side, quantity, activatePrice, callbackRate
       - Autenticação: mesma API Key (assinatura HMAC SHA256)
       - Logging: parâmetros + order_id retornado
[ ] 8.4 OrderManager.execute(): modo "trailing" → create_trailing_stop_order() no lugar do SL
[ ] 8.5 Testes V2 (2 cenários mínimos)
[ ] 8.6 ruff check + pytest
```

📄 `src/exchange/binance_client.py` · `src/config/settings.py` · `src/trading/order_manager.py`

### Fase 9: Finalização

```
[ ] 9.1 Validar docs/SDD/SPEC_030_SAIDA_DINAMICA/SPEC.md vs. implementação
[ ] 9.2 ruff check src/ tests/ --clean
[ ] 9.3 pytest tests/ -v --tb=short (full suite)
[ ] 9.4 Changelog + commit
```

---

## 6. Mapa de Mudanças por Arquivo

| Arquivo | Fase | Tipo | Linhas Estimadas | Risco | Depende de |
|---------|------|------|------------------|-------|------------|
| `src/config/settings.py` | 1 | Modificar | +40 | Baixo | — |
| `.env.example` | 1 | Modificar | +8 | Baixo | — |
| `src/trading/order_manager.py` | 2, 4 | Modificar | +80 | Médio | Fase 1, 3 |
| `src/exchange/simulated_client.py` | 3 | Modificar | +40 | Médio | — |
| `src/main.py` | 5 | Modificar | +15 | Baixo | Fase 4 |
| `tests/trading/test_exit_strategies.py` | 6 | Novo | +250 | Baixo | Fase 4 |
| `src/exchange/binance_client.py` | 7, 8 | Modificar | +50 | Alto (V2) | Fase 7 |
| `docs/SDD/SPEC_030_SAIDA_DINAMICA/SPEC.md` | 9 | Verificar | ~0 | — | Fase 1-8 |

**Total estimado V1:** ~425 linhas (5 arquivos modificados + 1 novo)
**Total estimado V2:** +~90 linhas (2 arquivos modificados)
**Esforço V1:** ~4-6h de implementação + 2-3h de testes
**Esforço V2:** ~3-4h (condicional)

---

## 7. Riscos e Mitigações

| Risco | Fase | Probabilidade | Impacto | Mitigação |
|-------|------|--------------|---------|-----------|
| Rollback complexo se TP2 falha após TP1 criar | 4 | Baixa | Alto | Rollback total (cancel_all_orders). Aceitar que perde TP1 também — segurança primeiro (P-004) |
| SimulatedClient não executa TPs automaticamente | 3 | Média | Médio | Adicionar check_and_execute_conditional_orders() para simular execução de condicionais |
| ccxt versão não suporta TRAILING_STOP_MARKET | 7 | Alta | Alto | Chamada REST direta ao /fapi/v1/algo (já é a abordagem definida em D-002) |
| Testnet sem suporte a Algo Order API | 7 | Média | Médio | V2 não testável em Testnet. Documentar risco. Aceitar em produção. |
| Config retrocompatível quebra trades abertos | 1 | Baixa | Médio | exit_strategy=fixed default. Trades abertos têm TP único — nenhuma mudança no comportamento. |

---

## 8. Questões em Aberto

1. **`exit_strategy` por símbolo ou global?** — SPEC_030 define "configurável por símbolo com fallback global". A implementação pode usar `exit_strategy_overrides: dict[str, str]` (similar a `atr_multiplier_overrides`) ou estender `SymbolConfig.from_triplet()` para `SYMBOL:TIMEFRAME:LEVERAGE:EXIT_STRATEGY`. **Recomendação:** `exit_strategy_overrides` — mais flexível, não quebra triplet parsing existente.

2. **Rollback parcial em TP?** — Se TP1 cria com sucesso mas TP2 falha, deve cancelar TUDO (incluindo TP1) ou manter TP1 e cancelar só TP2? **Decisão:** Cancelar tudo — posição parcialmente destravada sem proteção total é pior que não abrir.

3. **SimulatedClient precisa de engine de simulação de condicionais?** — No modo simulation, as ordens STOP_MARKET e TAKE_PROFIT_MARKET ficam "abertas" mas nunca executam porque não há loop de verificação de preço. **Decisão:** Adicionar `check_and_execute_conditional_orders()` chamado pela `TradingMonitor` no loop de 5min, similar ao `OrderMonitor`.

---

## 9. Critérios de Sucesso

- [ ] `pytest tests/ -v --tb=short` — 100% verde, 0 regressão
- [ ] `ruff check src/ tests/` — 0 erros
- [ ] TEST_030_01 a 09 implementados e passando
- [ ] Modo `fixed`: zero mudança de comportamento (testado comparativamente)
- [ ] Modo `partial`: N níveis de TP criados na abertura, SL nunca movido (verificado em log)
- [ ] SimulatedClient executa TP parcial (TEST_030_05)
- [ ] Config inválida = erro fatal no startup (verificado manualmente)
- [ ] V2: Verificação técnica documentada (ccxt versão + Testnet result)
- [ ] V2: create_trailing_stop_order() implementado (quando aplicável)
