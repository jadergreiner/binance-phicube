# Plan — SPEC_003: Inclusão de Cálculos de Margem e ROI Ajustado na Consulta de Posições

**spec_id:** SPEC_003
**status:** Revisado — pronto para tasks
**data:** 2026-05-02
**autor:** Time A (Refinamento)

---

## Rastreabilidade

```text
MANIFESTO.md
  └─ Princípio 3 (Transparência total) → métricas precisas de risco e performance
  └─ Princípio 4 (Configurabilidade) → cálculos baseados em dados existentes
        ↓
PRD.md — Fase 2 (Expansão) → "Dashboard de performance em tempo real"
  └─ Métricas aprimoradas para tomada de decisão
        ↓
SPEC_001 → Modelo PositionView base
        ↓
SPEC_002 → Contratos de API e frontend existentes
        ↓
SPEC_003 → Extensão com cálculos de margem e ROI ajustado (esta SPEC)
```

---

## Meta

- **spec_id:** SPEC_003
- **prd_fase:** Fase 2 — Expansão (`PRD.md › Dashboard de performance em tempo real`)
- **objetivo:** Estender SPEC_002 com cálculos de `position_size_usdt` (margem × alavancagem) e `roi_adjusted_pct` (P&L / tamanho × 100), exibindo no frontend e API para visibilidade precisa de exposição e retorno alavancado.
- **escopo:** Atualização de `PositionView`, cálculos no backend, extensão de contratos API/WebSocket, atualização frontend (tabela + resumo), mantendo backward compatibility.
- **fora_de_escopo:** Mudanças na estratégia, novos endpoints, histórico retroativo, alertas, modificações no RiskManager/OrderManager.
- **principios_manifesto_aplicados:** Princípios 3 (Transparência), 4 (Configurabilidade).

---

## Decisões Arquiteturais (Time A — sessão 2026-05-02)

| Decisão | Escolha | Justificativa |
|---|---|---|
| Local dos cálculos | Backend (PositionView) | Reutiliza dados existentes, evita duplicação no frontend, mantém consistência. |
| Campos novos | Opcionais no contrato | Backward compatible, permite evolução gradual. |
| Precisão | Float na API, Decimal interno | Compatibilidade com contratos existentes, precisão interna. |
| Validação | Invariantes no PositionView | Detecta dados inválidos da Binance, fallback seguro. |
| Frontend | Extensão da tabela existente | Reutiliza estrutura da SPEC_002, adiciona colunas. |

---

## Cenários de Risco Identificados

| Cenário | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| Dados inválidos da Binance (leverage=0) | Baixa | Campos incorretos | Invariante com fallback, log WARN. |
| Performance impact | Baixa | Lentidão no polling | Cálculos simples (multiplicação/divisão), <1ms por posição. |
| Interpretação errada do ROI | Média | Decisões ruins | Documentação clara no SPEC e tooltip no frontend. |

---

## Task Graph (Time A — sessão 2026-05-02)

### Tarefa 1: Atualizar PositionView com novos campos e cálculos
- **Descrição:** Adicionar `position_size_usdt` e `roi_adjusted_pct` ao modelo, implementar cálculos.
- **Dependências:** Nenhuma (base da SPEC_001).
- **Critérios de aceitação:** Unit tests passando para cálculos.
- **Prioridade:** Alta.
- **Estimativa:** 2h.

### Tarefa 2: Atualizar contratos de API (GET /positions, WS /ws/positions)
- **Descrição:** Incluir novos campos no JSON de resposta.
- **Dependências:** Tarefa 1.
- **Critérios de aceitação:** API retorna campos corretos.
- **Prioridade:** Alta.
- **Estimativa:** 1h.

### Tarefa 3: Atualizar frontend para exibir novos campos
- **Descrição:** Adicionar colunas na tabela, atualizar resumo.
- **Dependências:** Tarefa 2.
- **Critérios de aceitação:** Frontend renderiza campos corretamente.
- **Prioridade:** Alta.
- **Estimativa:** 1h.

### Tarefa 4: Testes unitários e integração
- **Descrição:** Cobrir cálculos, API, frontend.
- **Dependências:** Tarefas 1-3.
- **Critérios de aceitação:** 100% cobertura crítica, Testnet validado.
- **Prioridade:** Alta.
- **Estimativa:** 2h.

### Tarefa 5: Validação final e documentação
- **Descrição:** QA review, evidências para PR.
- **Dependências:** Tarefa 4.
- **Critérios de aceitação:** DoD SPEC_003 completo.
- **Prioridade:** Alta.
- **Estimativa:** 1h.

---

## Riscos de Dependência

- **SPEC_002 não concluída:** Baixo risco — SPEC_002 já aprovada.
- **Mudanças na Binance API:** Mitigado por fallback nos cálculos.

---

## Plano de Contingência

- Se cálculos complexos demais: Simplificar para margem × leverage apenas.
- Se frontend quebra: Rollback para versão sem novos campos.

---
