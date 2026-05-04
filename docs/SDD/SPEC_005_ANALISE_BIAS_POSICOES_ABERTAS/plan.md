# Plan — SPEC_005: Análise de Bias de Mercado e Oportunidades de Posições Abertas

**spec_id:** SPEC_005
**status:** Em Refinamento
**data:** 2026-05-03
**autor:** Time A (Refinamento)

---

## Rastreabilidade

```text
MANIFESTO.md
  └─ Princípio 2 (Gestão de risco) -> visibilidade de bias de mercado
  └─ Princípio 3 (Transparência) -> análise clara de exposição
        ↓
PRD.md — Monitoramento de risco e posições abertas
        ↓
docs/SDD/SPEC.md — Contratos de dashboard e API de posições
        ↓
SPEC_005 — análise de bias e oportunidades de trade na base de posições abertas
```

---

## Meta

- **objetivo:** Formalizar e entregar a análise de bias de mercado a partir das posições abertas do dashboard.
- **escopo:** análise de bias, serialização em `/positions`, atualizações por WebSocket, modelagem de `MarketAnalysis` e testes.
- **fora_de_escopo:** previsão de preço, ordens automáticas e análise histórica.
- **principios_manifesto_aplicados:** Princípios 2 (Risco), 3 (Transparência), 5 (Clareza Operacional).

---

## Decisões Arquiteturais

- Usar `src/dashboard/analysis.py` como núcleo da análise de bias.
- Expor `analysis` no mesmo payload de snapshot utilizado pelo dashboard de posições.
- Manter o módulo independente de lógica de execução de ordens.
- Tratar exposição inválida como caso não fatal.

---

## Fases

1. **Fase 1 - Contrato de Análise**
   - Definir modelos `MarketBias`, `TradeOpportunity`, `MarketAnalysis`.
   - Confirmar cálculo de `score`, `confidence` e `reason`.

2. **Fase 2 - Integração API e UI**
   - Garantir que o endpoint `/positions` retorna `analysis`.
   - Validar stream WebSocket e serialização no painel.

3. **Fase 3 - Testes e Validação**
   - Adicionar testes unitários em `tests/dashboard/test_analysis.py`.
   - Executar testes de integração de endpoint e stream.

4. **Fase 4 - Documentação e Entrega**
   - Atualizar `docs/SDD/README.md` e status do SPEC.
   - Preparar evidências para PR.

---

## Dependências

- `src/dashboard/analysis.py`
- `src/dashboard/models.py`
- `src/api/routes/positions.py`
- `src/dashboard/ui.py`
- `tests/dashboard/test_analysis.py`

---

## Critérios de Pronto do Plano

- [ ] Contratos de análise revisados e documentados.
- [ ] Endpoint e stream retornam objeto `analysis` corretamente.
- [ ] Testes unitários e integração definidos e passando.
- [ ] Arquivos de SPEC e plano criados e rastreados.
