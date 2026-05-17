# SPEC - Implementação PhiCube no binance-phicube

## 1. Metadados

- **ID:** SPEC-PHI-001
- **Status:** Em revisão
- **Autor:** Davi Orchestrator + Refiners
- **Data:** 2026-05-17
- **Origem:** Evolução de produto
- **Relacionados:**
  - `.davi/project-knowledge/business/phicube-rules.catalog.md`
  - `.davi/project-knowledge/business/phicube-rules.model.json`
  - `.davi/project-knowledge/business/phicube-rules.pending.md`
  - `docs/phicube_combined_standalone.pdf`
  - `docs/phicube_combined_standalone.extracted.txt`

---

## 2. Contexto e Objetivo

### Contexto

As regras RN-PHI já estão mapeadas, mas ainda não operacionalizadas de forma
determinística no motor. Há enriquecimento parcial de diagnóstico técnico, sem
pipeline completo de decisão por regras.

### Objetivo

Implementar lógica PhiCube rastreável e segura com modos `shadow`, `advisory`
e `active`.

### Resultado esperado

Motor de sinal com `rule_hits`, `reason`, `estado_mercado` e
`explicacao_humana`, com promoção por gates e rollback por flag.

---

## 3. Escopo

### Dentro do escopo

- Plugin/estratégia PhiCube v1
- Integração com engine atual sem regressão
- Diagnóstico operacional em PT-BR com explicação não técnica
- Testes unitários, de contrato e de integração
- Rollout controlado por modo

### Fora do escopo

- Reescrita total do SignalEngine
- Inferência de fórmulas proprietárias não públicas
- Otimização além da estabilidade v1

---

## 4. Requisitos

### Requisitos Funcionais

- **RF-01:** Expor estado de mercado em PT-BR com explicação humana:
  - `alta_forte`: os sinais apontam subida consistente
  - `baixa_forte`: os sinais apontam queda consistente
  - `consolidacao`: o preço está sem direção clara
  - `transicao`: o mercado está mudando de comportamento
- **RF-02:** Emitir `SignalResult`/`NullSignalResult` com `reason` e `rule_hits`.
- **RF-03:** Suportar modos `shadow`, `advisory`, `active`.
- **RF-04:** Suportar thresholds globais + overrides por `symbol/timeframe`.
- **RF-05:** Expor diagnóstico PhiCube estruturado na API de símbolo.
- **RF-06:** Registrar eventos de decisão e bloqueio para RCA.

### Requisitos Não Funcionais

- **RNF-01:** Reprodutibilidade de decisão.
- **RNF-02:** Backward compatibility com feature flag desligada.
- **RNF-03:** Promoção de modo com gate formal e aprovação humana.
- **RNF-04:** Cobertura unit/contract/integration.
- **RNF-05:** Rollback imediato por flag.
- **RNF-06:** Versionamento/auditoria de regras e thresholds.

---

## 5. Contratos e Regras

### Entradas

- `symbol`, `timeframe`, candles fechadas
- `phicube_enabled`, `phicube_mode`
- thresholds globais e overrides por `symbol/timeframe`

### Saídas

- `SignalResult` ou `NullSignalResult`
- Diagnóstico:
  - `estado_mercado`
  - `explicacao_humana`
  - `rule_hits`
  - `reason`

### Regras de negócio / decisão

- **RN-PHI núcleo v1:** RN-PHI-003..016 e RN-PHI-024
- **RN-PHI governança:** RN-PHI-023..025
- **RN-PHI fase posterior:** RN-PHI-017..022

### Casos de erro ou exceção

- dados insuficientes -> `NullSignalResult(reason=insufficient_data)`
- config inválida -> bloqueio com `reason=config_invalid`
- modo `shadow` -> nunca executar ordem

---

## 6. Plano de Entrega / Decomposição Inicial

- **T01:** Contrato de configuração PhiCube
- **T02:** Plugin PhiCube v1 (RN-PHI-003..016, 024)
- **T03:** Integração SignalEngine/Registry
- **T04:** Diagnóstico operacional/API
- **T05:** Observabilidade e eventos
- **T06:** Testes unitários
- **T07:** Testes de contrato (API)
- **T08:** Testes de integração
- **T09:** Rollout `shadow -> advisory -> active`
- **T10:** Documentação final e handoff

### Dependências

- T02 depende de T01
- T03 depende de T02
- T04/T05 dependem de T03
- T06 depende de T02
- T07 depende de T04
- T08 depende de T03/T06/T07
- T09 depende de T08
- T10 depende de T09

---

## 7. Critérios de Aceite

- **CA-01:** Sem regressão com `phicube_enabled=false`
- **CA-02:** Zero ordens em `shadow`
- **CA-03:** `estado_mercado` em PT-BR no diagnóstico
- **CA-04:** `explicacao_humana` não técnica presente
- **CA-05:** `reason` e `rule_hits` registrados
- **CA-06:** Cobertura unit do núcleo v1
- **CA-07:** Contratos de API aprovados
- **CA-08:** Integração engine+flags aprovada
- **CA-09:** Promoção de modo só com gates + aprovação humana
- **CA-10:** Rollback por flag comprovado

---

## 8. Observabilidade e Evidências

### Evidências mínimas esperadas

- Testes unit/contract/integration
- Evidência por modo (`shadow`, `advisory`, `active`)
- Logs: `estado_mercado`, `explicacao_humana`, `reason`, `rule_hits`,
  `phicube_mode`
- Evidência de rollback por flag

### Sinais de sucesso

- Completude de diagnóstico > 99%
- Sem regressão de contrato
- Promoção com aprovação humana registrada
- RCA viável por logs

---

## 9. Decisões e Pendências

### Decisões já assumidas

- Plugin PhiCube separado
- Rollout `shadow -> advisory -> active`
- Estado em PT-BR com explicação não técnica
- Núcleo v1: RN-PHI-003..016 + RN-PHI-024
- Sem inferência de fórmulas proprietárias

### Pendências em aberto

- Calibração fina de thresholds por `symbol/timeframe`
- Estratégia final para RN-PHI-017..022
- Critérios de promoção para escala ampla

## Status

Approved by human (SPEC stage).
