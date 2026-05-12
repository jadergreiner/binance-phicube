# PLAN — Execution Plan: SPEC_028 Realismo em Backtest

**ID:** PLAN-028
**Responsável:** Product Owner
**SPEC vinculada:** SPEC_028 (v2.0)
**PRD vinculado:** PRD.md (v1.0)
**Estimativa total:** 6-7 dias (ideal) / 8-10 dias (com buffer)
**Dependências:** SPEC_011 (Motor de Backtesting) — Concluída

---

## 1. Visão Geral

Backtest realista com slippage por tier de liquidez, taxas Binance e sizing via RiskManager. Feature P1 — necessária antes de qualquer tomada de decisão de produção baseada em backtest.

### Por que agora?

O backtest atual produz PnL **2x maior que a realidade** e não contabiliza custos. O operador não pode confiar nos resultados para decidir se opera ou não uma estratégia. Sem esta feature, backtest é entretenimento, não ferramenta de decisão.

---

## 2. Escopo

### ✅ No escopo (entrega obrigatória)

| Item | User Story | Esforço | Prioridade |
|------|-----------|---------|------------|
| Slippage percentual por tier de liquidez (3 tiers + lookup map) | US-028-01 | 1 dia | P0 — base |
| Taxas maker/taker com defaults Binance VIP 0 | US-028-01 | 0,5 dia | P0 — base |
| Flag `--realistic` no CLI + `realistic=true` na API | US-028-01 | 0,5 dia | P0 — base |
| RiskManager integrado ao cálculo de PnL (sizing real) | US-028-03 | 1,5 dia | P0 — core |
| Resultado Gross/Net lado a lado | US-028-02 | 0,5 dia | P0 — core |
| Alerta informacional composto (IC, net/gross, N, multi-run) | US-028-04 | 1 dia | P1 — valor |
| Logging de parâmetros em JSONL (sempre ativo) | US-028-05 | 0,5 dia | P1 — valor |
| Override de slippage com WARN | US-028-01 | 0,5 dia | P1 — valor |
| Testes (TEST_028_01 a 11) | — | 1 dia | P0 — qualidade |

### ❌ Fora do escopo (não entregar agora)

| Item | Motivo | Quando? |
|------|--------|---------|
| Slippage estocástico | Impacto <0,3% do PnL. ROI negativo. | Reavaliar pós walk-forward |
| Saldo virtual (equity variável) | Custo alto (dias) para ganho incremental. | SPEC_029 (ATR Sizing) |
| Spread observado via order book | Requer coleta histórica de dados. | SPEC futura |
| Detector de overfitting automático | Depende do logging que estamos construindo. | SPEC futura |

---

## 3. Fases de Entrega

Organizado em 3 fases sequenciais — cada fase termina com um **gate de qualidade** (testes verdes + lint limpo).

### Fase 1 — Fundação (Dias 1-2)

**Objetivo:** Slippage e Taxas operacionais no modelo de dados e engine.

| Tarefa | ID Técnica | Artefato | Critério de Aceite |
|--------|-----------|----------|-------------------|
| Extender `BacktestTrade` e `BacktestResult` com campos de custo | MD-01 | `models.py` | Campos `entry_fee`, `exit_fee`, `slippage_entry_pct`, `slippage_exit_pct`, `pnl_gross_usdt`, `pnl_net_usdt`, `gross`, `net`, `warnings` |
| Adicionar settings de slippage por tier e taxas | MD-02 | `settings.py` | `BACKTEST_SLIPPAGE_BY_LIQ`, `BACKTEST_SLIPPAGE_LIQ_MAP`, `BACKTEST_MAKER_FEE`, `BACKTEST_TAKER_FEE` |
| Implementar `_apply_costs` no BacktestEngine | EN-01 | `engine.py` | Slippage + fee aplicados corretamente por direção e tipo de ordem |
| Adicionar `--realistic` flag no CLI | CL-01 | `runner.py` | Flag parseada e passada ao engine |
| Adicionar `realistic` query param na API | AP-01 | `routes/backtest.py` | Parâmetro aceito e repassado |

**Gate Fase 1:**
- [ ] TEST_028_01 (long realistic) passando
- [ ] TEST_028_02 (short realistic) passando
- [ ] TEST_028_03 (override=0) passando
- [ ] `ruff check src/ tests/` limpo

---

### Fase 2 — Sizing Real (Dias 3-4)

**Objetivo:** RiskManager integrado ao PnL do backtest.

| Tarefa | ID Técnica | Artefato | Critério de Aceite |
|--------|-----------|----------|-------------------|
| Injetar RiskManager opcional no BacktestEngine | EN-02 | `engine.py` | `__init__` aceita `risk_manager: RiskManager \| None` |
| Substituir fórmula de PnL no modo realista | EN-03 | `engine.py` | `pnl = (exit_price - entry) * position.quantity` |
| Preservar fórmula linear no modo legado | EN-04 | `engine.py` | `--realistic` ausente → comportamento SPEC_011 |
| Serializar Gross e Net lado a lado | MD-03 | `models.py` + `runner.py` | Ambos os resultados no output CLI e API |

**Gate Fase 2:**
- [ ] TEST_028_04 (compatibilidade reversa) passando
- [ ] TEST_028_05 (API gross/net distintos) passando
- [ ] TEST_028_06 (PnL RiskManager ≠ fórmula linear) passando
- [ ] `pytest tests/backtest/test_engine.py` 100% verde (testes SPEC_011 intactos)

---

### Fase 3 — Inteligência e Auditabilidade (Dias 5-7)

**Objetivo:** Alertas informacionais, logging de parâmetros, testes finais.

| Tarefa | ID Técnica | Artefato | Critério de Aceite |
|--------|-----------|----------|-------------------|
| Implementar `_build_warnings` no engine | EN-05 | `engine.py` | 4 condições monitoradas (N<50, net/gross<0.5, combinado, multi-run) |
| Exibir alertas no CLI | CL-02 | `runner.py` | Seção `⚠️ Análise de Confiabilidade` no output |
| Expor `warnings` na API | AP-02 | `routes/backtest.py` | Campo `warnings: list[str]` no JSON |
| Implementar logging JSONL | EN-06 | `engine.py` | Append em `backtest_runs.jsonl` |
| Implementar `--override-slippage` com WARN | EN-07 | `engine.py` + `runner.py` | Override aceito, WARN no log |
| Testes de alerta e logging | TS-01 | `test_spec028.py` | TEST_028_07 a 11 |

**Gate Fase 3:**
- [ ] TEST_028_07 a 11 passando
- [ ] Output CLI com alerta informacional funcional
- [ ] `backtest_runs.jsonl` populado após execução
- [ ] `ruff check src/ tests/` limpo

---

## 4. Matriz de Dependências

```
Fase 1 (Slippage + Taxas)
  │
  ├── Fase 2 (Sizing Real)
  │     └── depende de: RiskManager existente (já implementado)
  │
  └── Fase 3 (Alertas + Logging)
        └── depende de: Fase 1 (dados de custo para os alertas)
        └── depende de: Fase 2 (Gross/Net para o alerta de degradação)
```

**Caminho crítico:** Fase 1 → Fase 2 → Fase 3. Nenhuma fase pode pular a anterior.

**Paralelizável:** Nada neste escopo. As dependências são sequenciais.

---

## 5. Riscos e Mitigações

| Risco | Prob. | Impacto | Gatilho | Mitigação |
|-------|-------|---------|---------|-----------|
| RiskManager existente tem bug de position sizing | Baixa | Alto (PnL incorreto) | Fase 2 | Incluir TEST_028_06 comparando com fórmula linear. Validar em Testnet depois. |
| Testes SPEC_011 quebram por mudança no modelo | Média | Alto (CI falha) | Fase 1 | Executar `pytest tests/backtest/test_engine.py` a cada commit. Compatibilidade é invariante. |
| Slippage por tier não reflete liquidez real do par | Média | Médio (resultado irreal) | Fase 1 | Override disponível. Tier map ajustável via settings. |
| Feature estoura estimativa de 7 dias | Média | Médio (atrasa outras SPECs) | Fase 3 | Buffer de 3 dias já incluído. Se ultrapassar 10 dias, replanejar. |

---

## 6. Critérios de Pronto (Definition of Done)

- [ ] SPEC_028 implementada conforme v2.0
- [ ] 11 testes (TEST_028_01 a 11) passando
- [ ] `pytest tests/backtest/test_engine.py` inalterado (compatibilidade)
- [ ] `ruff check src/ tests/` limpo
- [ ] Output CLI de demonstração validado com 1 par BTC e 1 par ADA
- [ ] API testada com `realistic=true` e `realistic=false`
- [ ] PRD atualizado se houve mudança de escopo
- [ ] README.md das SDDs atualizado

---

## 7. Sign-off

| Papel | Nome | Data | Assinatura |
|-------|------|------|------------|
| Product Owner | (você) | 2026-05-10 | ✅ |
| Trader Sênior | Time A | 2026-05-10 | ✅ (refinamento) |
| Risk Manager | Time A | 2026-05-10 | ✅ (refinamento) |

---

## 8. Próximos Passos

1. ✅ **Time A** — Refinamento concluído (SPEC v2.0 + PRD + PLAN)
2. ⬜ **Planner Agent** — Gerar Task Graph técnico (TG-001 a TG-XXX)
3. ⬜ **Dev Agent** — Implementar por fases (Fase 1 → 2 → 3)
4. ⬜ **Validation Agent** — Validar conformidade com SPEC
5. ⬜ **Gate/Commit** — Revisão final e merge

---

## Histórico

| Versão | Data | Autor | Mudanças |
|--------|------|-------|----------|
| 1.0 | 2026-05-10 | Product Owner | Plano inicial pós-refinamento SPEC_028 |
