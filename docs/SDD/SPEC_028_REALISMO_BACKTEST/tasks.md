## Task Graph — SPEC_028 Realismo em Backtest

**Esforço total estimado:** 6-7 dias
**Dependências:** SPEC_011 (Concluída)
**Pipeline:** Fase 1 → Fase 2 → Fase 3 (sequencial obrigatório)
**Status:** ✅ **100% COMPLETO** (14/14 TG concluídos)

---

### Fase 1 — Fundação (Slippage + Taxas) ✅

**TG-001 [P0] ✅ Estender modelo de dados com campos de custo**
- `origem_spec`: seção 4 — Modelo de Dados
- `deps`: —
- `owner`: Backend
- `done_when`: `BacktestTrade` possui `entry_fee`, `exit_fee`, `slippage_entry_pct`, `slippage_exit_pct`, `slippage_entry_usdt`, `slippage_exit_usdt`, `pnl_gross_usdt`, `pnl_net_usdt`. `BacktestResult` possui `gross`, `net`, `total_fees_usdt`, `total_slippage_usdt`, `warnings`. Ambos serializáveis para JSON. `gross` e `net` sempre presentes (`gross == net` quando não-realista).
- `evidência`: `pytest tests/backtest/test_realistic.py::TEST_028_04`
- `risco`: baixo — mudança aditiva em dataclasses, sem quebra de contrato existente

**TG-002 [P0] ✅ Adicionar configurações de slippage por tier e taxas**
- `origem_spec`: seção 5.1 — Configuração
- `deps`: —
- `owner`: Backend
- `done_when`: `Settings` possui `BACKTEST_SLIPPAGE_BY_LIQ` (dict com 3 tiers: high/medium/low), `BACKTEST_SLIPPAGE_LIQ_MAP` (dict com mapeamento dos 31+ símbolos), `BACKTEST_MAKER_FEE` (0.02%), `BACKTEST_TAKER_FEE` (0.05%). `BACKTEST_SLIPPAGE_FLAT` e `BACKTEST_SLIPPAGE_PCT` removidos.
- `evidência`: teste de leitura de configuração + validação manual
- `risco`: baixo — campos novos em Pydantic BaseSettings

**TG-003 [P0] ✅ Implementar `_apply_costs` no BacktestEngine**
- `origem_spec`: seção 5.2 — `_apply_costs`
- `deps`: TG-001, TG-002
- `owner`: Backend / Quant
- `done_when`: Método `_apply_costs(price, direction, symbol, order_type)` retorna `(price_with_slippage, fee_amount, slippage_amount)`. LONG entry: +slippage. SHORT entry: −slippage. Stop orders usam maker_fee. Market orders usam taker_fee. INV-028-01, 02, 03 respeitados.
- `evidência`: `pytest tests/backtest/test_realistic.py::TEST_028_01` e `TEST_028_02`
- `risco`: médio — algoritmo de ajuste de preço por direção precisa estar correto para não inverter PnL

**TG-004 [P0] ✅ Adicionar `--realistic` flag no CLI runner**
- `origem_spec`: seção 5.6 — Runner CLI
- `deps`: TG-003
- `owner`: Backend
- `done_when`: `python -m src.backtest.runner --symbol BTCUSDT --timeframe 4h --realistic` executa e exibe saída com `total_fees`, `total_slippage`. Sem `--realistic`, saída idêntica à SPEC_011.
- `evidência`: execução manual + `TEST_028_04`
- `risco`: baixo — argparse adicional

**TG-005 [P0] ✅ Adicionar `realistic` query param na API**
- `origem_spec`: seção 5.7 — API
- `deps`: TG-003
- `owner`: Backend
- `done_when`: `GET /backtest?symbol=BTCUSDT&timeframe=4h&realistic=true` retorna 200 com `gross` e `net` distintos no JSON. `realistic=false` ou omitido retorna resposta SPEC_011.
- `evidência`: `TEST_028_05`
- `risco`: baixo — FastAPI query param adicional

---

### Fase 2 — Sizing Real (RiskManager) ✅

**TG-006 [P0] ✅ Integrar RiskManager ao BacktestEngine**
- `origem_spec`: seção 5.3 — RiskManager Integration
- `deps`: TG-003
- `owner`: Backend / Quant
- `done_when`: `BacktestEngine.__init__` aceita `risk_manager: RiskManager | None`. Quando `--realistic` ativo, `RiskManager.calculate()` dimensiona posição e PnL usa `(exit_price - entry) * position.quantity`. Quando não-realista, fórmula linear original preservada. INV-028-04 e 05 respeitados.
- `evidência`: `TEST_028_06` (PnL RiskManager ≠ fórmula linear no mesmo cenário) + `pytest tests/backtest/test_engine.py` 100% verde (compatibilidade SPEC_011)
- `risco`: alto — RiskManager existente pode ter edge cases. Risco mitigado por: inject opcional + compatibilidade reversa com testes SPEC_011 intactos

**TG-007 [P0] ✅ Serializar Gross e Net lado a lado**
- `origem_spec`: seção 4 (Modelo) + seção 3 (US-028-02)
- `deps`: TG-006
- `owner`: Backend
- `done_when`: Output CLI exibe `Gross PnL` e `Net PnL` lado a lado quando `--realistic`. API retorna ambos no JSON. Quando não-realista, ambos os valores são idênticos.
- `evidência`: `TEST_028_05` (API gross/net distintos)
- `risco`: baixo — formatação de output

---

### Fase 3 — Inteligência e Auditabilidade ✅

**TG-008 [P1] ✅ Implementar alerta informacional composto**
- `origem_spec`: seção 5.4 — Alerta Informacional
- `deps`: TG-007 (precisa de Gross/Net), TG-010 (precisa de JSONL para alerta de multi-run)
- `owner`: Backend
- `done_when`: 4 condições implementadas: (a) N < 50 → IC win rate; (b) net/gross < 0.5 → degradação alta; (c) ambas → alerta vermelho; (d) >3 runs mesmo par 24h → data dredging. Nenhuma bloqueia execução (exit code 0). `BacktestResult.warnings` populado. INV-028-06 respeitado.
- `evidência`: `TEST_028_07`, `TEST_028_08`, `TEST_028_09`
- `risco`: médio — lógica de contagem de runs nas últimas 24h precisa de parser de JSONL + window de tempo

**TG-009 [P1] ✅ Exibir alertas no output CLI**
- `origem_spec`: seção 5.4 (exemplo de saída)
- `deps`: TG-008
- `owner`: Backend
- `done_when`: CLI exibe seção `⚠️ Análise de Confiabilidade:` com as mensagens de alerta ao final do output, quando aplicável.
- `evidência`: execução manual com N < 50 e net/gross < 0.5
- `risco`: baixo — formatação de string

**TG-010 [P1] ✅ Expor `warnings` na API**
- `origem_spec`: seção 5.7 (resposta JSON)
- `deps`: TG-008
- `owner`: Backend
- `done_when`: `GET /backtest?realistic=true` retorna campo `warnings: list[str]` no JSON. Array vazio quando nenhum alerta.
- `evidência`: `TEST_028_05` (extensão — validar campo warnings presente)
- `risco`: baixo — serialização de lista

**TG-011 [P1] ✅ Implementar logging de parâmetros em JSONL**
- `origem_spec`: seção 5.5 — Logging
- `deps`: TG-007 (precisa de gross/net para logar)
- `owner`: Backend
- `done_when`: Cada execução de `run()` append em `backtest_runs.jsonl` com timestamp, symbol, timeframe, params, gross_pnl, net_pnl, n_trades, warnings. Log ativo independentemente de `--realistic`. Falha de escrita não interrompe backtest. INV-028-07 respeitado.
- `evidência`: `TEST_028_10`
- `risco`: baixo — IO append-only. Risco de concorrência mitigado por rate-limit de 1 linha/segundo.

**TG-012 [P1] ✅ Implementar `--override-slippage` com WARN**
- `origem_spec`: seção 5.6 (flag `--override-slippage`)
- `deps`: TG-003 (precisa de `_apply_costs`)
- `owner`: Backend
- `done_when`: `--override-slippage 0.002` sobrescreve slippage do tier. WARN no log: "override-slippage ativo — resultado pode não refletir liquidez real do par". Slippage clampado em 0.0 mínimo.
- `evidência`: `TEST_028_11` + log contém WARN esperado
- `risco`: baixo — override simples com validação

---

### Testes e Qualidade

**TG-013 [P0] ✅ Escrever suite de testes TEST_028_01 a 11 (33 testes)**
- `origem_spec`: seção 7 — Testes
- `deps`: TG-001 a TG-012 (cada teste depende da feature que testa)
- `owner`: QA / Backend
- `done_when`: 11 testes implementados e passando. `pytest tests/backtest/test_realistic.py` verde. `pytest tests/backtest/test_engine.py` inalterado.
- `evidência`: CI green
- `risco`: médio — testes de alerta multi-run dependem de clock. Usar `freezegun` ou mock de timestamp.

**TG-014 [P0] ✅ Validar compatibilidade reversa com SPEC_011**
- `origem_spec`: seção 6 (INV-028-05) + seção 9 (DoD)
- `deps`: TG-001 a TG-012
- `owner`: QA
- `done_when`: `pytest tests/backtest/test_engine.py` sem falhas. Execução sem `--realistic` produz resultado idêntico ao SPEC_011.
- `evidência`: CI green + diff de output vs. baseline SPEC_011
- `risco`: baixo — invariante verificável por CI

---

### Documentação

**TG-015 [P1] ✅ Atualizar documentação**
- `origem_spec`: seção 8 (Arquivos — README.md)
- `deps`: TG-014 (DoD completo)
- `owner`: DocWriter
- `done_when`: `docs/SDD/README.md` atualizado com entrada SPEC_028 e data da implementação.
- `evidência`: diff do README
- `risco`: baixo — edição de markdown

---

### Grafo de Dependências

```
TG-001 ─┐
TG-002 ─┤
         ├── TG-003 ──┬── TG-004 ──┐
         │            └── TG-005 ──┤
         │                         │
TG-006 ──┤ (deps: TG-003) ── TG-007
         │
TG-012 ──┤ (deps: TG-003)
         │
TG-008 ──┤ (deps: TG-007, TG-011)
         │        │
TG-009 ──┤ (deps: TG-008)
TG-010 ──┤ (deps: TG-008)
         │
TG-011 ──┤ (deps: TG-007)
         │
TG-013 ──┤ (deps: TG-001..012)
TG-014 ──┤ (deps: TG-001..012)
TG-015 ──┤ (deps: TG-014)
```

**Caminho crítico:** TG-001 → TG-003 → TG-006 → TG-007 → TG-008 → TG-013 → TG-014 → TG-015

**Ordem de execução recomendada:** TG-001 + TG-002 (paralelo) → TG-003 → TG-004 + TG-005 + TG-012 (paralelo) → TG-006 → TG-007 → TG-011 → TG-008 → TG-009 + TG-010 (paralelo) → TG-013 + TG-014 (paralelo) → TG-015

---

### Riscos do Task Graph

| Risco | TG afetado | Impacto | Mitigação |
|-------|-----------|---------|-----------|
| RiskManager tem bug não detectado | TG-006 | PnL realista incorreto | Comparar PnL de 50 trades simulados vs. Testnet real |
| Testes SPEC_011 quebram por mudança no modelo | TG-014 | CI falha | Rodar `pytest tests/backtest/test_engine.py` a cada commit |
| Alerta multi-run depende de clock real | TG-008 | Testes instáveis | Usar `freezegun` ou mock de `datetime.utcnow()` |
