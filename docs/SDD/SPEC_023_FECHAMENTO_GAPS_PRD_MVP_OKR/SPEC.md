# SPEC_023 — Fechamento de Gaps do PRD (MVP + OKR Atuais)

**ID:** SPEC_023
**Status:** Em Execucao
**Data:** 2026-05-07
**Autor:** Time A (Refinamento)
**Executores:** Time B (Execucao)
**Skill de validacao:** `sdd-spec-driven-development`, `qa-review`

---

## 1. Titulo e Resumo

### 1.1 Nome da Funcionalidade

Fechamento de Gaps do PRD (MVP + OKR Atuais)

### 1.2 Resumo

Pacote dedicado para fechar lacunas remanescentes entre metas do PRD e evidencias implementadas.
Escopo em modo hibrido: engenharia e automacao nesta rodada, com gate operacional real (soak 48h e lote de execucoes Testnet) como etapa final objetiva.

---

## 2. Objetivos e Escopo

### 2.1 Objetivos

- [ ] Entregar rastreabilidade PRD -> SPEC -> testes -> codigo para todos os gaps pendentes no escopo MVP/OKR atual.
- [ ] Implementar politica tecnica explicita de retencao minima de 90 dias para dados operacionais de trade/audit.
- [ ] Ampliar robustez de testes de risco para matriz com 50+ cenarios.
- [ ] Entregar scripts de evidencia operacional: auditoria de 50 execucoes Testnet, cobertura estrita > 80.0 e orquestrador de soak.
- [ ] Integrar validacao automatizada dos artefatos de fechamento.

### 2.2 Fora do Escopo

- [ ] Fechar operacionalmente o soak real de 48h nesta mesma sessao.
- [ ] Relaxar criterio PRD de 100% para execucoes Testnet.
- [ ] Implementar itens de Fase 2 (walk-forward, auto-ajuste de parametros, multiplas estrategias).

---

## 3. Referencias

| Documento | Relevancia |
|---|---|
| `PRD.md` | Requisitos e metas MVP/OKR em aberto (48h, 50 cenarios, 50 execucoes, 80%+, retencao) |
| `docs/SDD/SPEC_021_VALIDACAO_OPERACIONAL_RESILIENCIA/` | Gate de soak e evidencia operacional |
| `src/storage/repository.py` | Politica de indices/TTL |
| `src/config/settings.py` | Contrato de configuracao para retencao |
| `src/trading/risk_manager.py` | Motor de sizing para matriz de cenarios |

---

## 4. Requisitos

### US-023-01 — Retencao Minima de 90 Dias

- [ ] AC-01: configuracao `TRADE_HISTORY_RETENTION_DAYS` com minimo 90 e default 90.
- [ ] AC-02: indice TTL operacional de trades/audit respeita valor configurado (>= 90 dias).
- [ ] AC-03: TTL de heartbeat continua dedicado e nao reduz retencao dos demais eventos.

### US-023-02 — Matriz de Risco 50+ Cenarios

- [ ] AC-01: suite parametrizada com pelo menos 50 cenarios de sizing.
- [ ] AC-02: cobertura de cenarios inclui stop distance, rounding, min_notional, alocacao e leverage limite.
- [ ] AC-03: invariantes de seguranca do RiskManager permanecem sem regressao.

### US-023-03 — Evidencias Operacionais Automatizadas

- [ ] AC-01: harness gera `reports/spec023_order_exec_audit.json` com total, sucesso, falha e causas.
- [ ] AC-02: orquestrador gera `soak_evidence.json` no contrato canonico SPEC_021.
- [ ] AC-03: validador automatizado falha quando cobertura <= 80.0, quando auditoria de 50 execucoes nao atinge 100% ou quando soak invalido.

---

## 5. Testes e Validacao

- [ ] `pytest` de regressao dos modulos impactados (`config`, `storage`, `risk_manager`, `order_manager`).
- [ ] `pytest` da matriz de risco 50+ cenarios.
- [ ] Gate de cobertura estrita (`> 80.0`) com artefato JSON.
- [ ] Gate de auditoria de execucoes Testnet (50 / 100%).
- [ ] Gate de soak via `validate_soak_evidence.py`.

---

## 6. Definicao de Pronto (DoD)

- [ ] SPEC_023 com tasks e status coerentes.
- [ ] Politica de retencao >= 90 dias implementada e testada.
- [ ] Matriz de risco 50+ cenarios entregue.
- [ ] Scripts de evidencia operacional entregues e validados.
- [ ] Rastreabilidade consolidada em `spec_status_update.md`.

---

## 7. Historico

- **2026-05-07:** Criacao da SPEC_023 para fechamento de gaps PRD MVP/OKR.
