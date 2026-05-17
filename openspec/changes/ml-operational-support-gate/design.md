## Contexto

A change `ml-operational-support-gate` define a introdução de uma camada de ML como apoio operacional ao BO Williams. Nesta fase, a execução real deve permanecer inalterada. O foco é observabilidade, comparabilidade com baseline e segurança de rollout.

## Objetivo de Design

Definir uma arquitetura incremental que permita:

- calcular score preditivo por símbolo/timeframe;
- registrar decisão auxiliar ML em paralelo ao fluxo atual;
- habilitar ativação progressiva por feature flags;
- comparar impacto contra baseline BO puro;
- garantir rollback instantâneo sem impacto operacional.

## Escopo (Fase atual)

- Shadow mode obrigatório.
- Sem bloqueio real de ordens por ML.
- Sem alteração no contrato do `OrderManager`.
- Sem substituição do `SignalEngine`.

## Arquitetura Proposta

### 1) Camada de inferência auxiliar

Novo componente lógico (ex.: `MlSignalSupportService`) invocado após avaliação do BO:

- Entrada mínima:
  - `symbol`, `timeframe`
  - snapshot de features técnicas (ex.: AO, alinhamento alligator, volatilidade, regime)
  - resultado do BO (detectado/não detectado + direção)
- Saída:
  - `ml_score` (0-1)
  - `ml_decision` (`ALLOW`, `BLOCK`, `ABSTAIN`)
  - `ml_reason` (string curta e rastreável)
  - `model_version`

Nesta fase, `ml_decision` não altera o caminho de execução real.

### 2) Ponto de integração

Integração no fluxo do monitor imediatamente após `SignalEngineBoundary.evaluate(...)`:

- BO continua sendo fonte única de decisão operacional.
- ML executa em paralelo para diagnóstico.
- Resultado ML é persistido em trilha de auditoria e (quando aplicável) anexado ao diagnóstico do ciclo.

### 3) Persistência e diagnóstico

Expandir payload de diagnóstico de ciclo (`signal_cycle_diagnostic`) com campos ML:

- `ml_enabled` (bool)
- `ml_shadow_mode` (bool)
- `ml_score` (float | null)
- `ml_decision` (string | null)
- `ml_reason` (string | null)
- `ml_model_version` (string | null)

Garantir compatibilidade retroativa: campos opcionais e nulos quando indisponíveis.

### 4) Feature Flags

Flags por símbolo/timeframe com fallback global:

- `ml_support_enabled` (global)
- `ml_support_shadow_mode` (global, default true)
- `ml_support_symbol_timeframes` (lista opcional para canário)
- `ml_support_min_score` (threshold futuro)

Comportamento nesta fase:

- Se desabilitado: não executa inferência ML.
- Se habilitado e shadow=true: executa e registra, sem impacto operacional.

### 5) Observabilidade

Adicionar métricas e logs estruturados:

- contagem de inferências ML por símbolo/timeframe;
- distribuição de score;
- taxa de `ALLOW/BLOCK/ABSTAIN`;
- latência da inferência;
- taxa de falha da inferência (com fallback silencioso para BO puro).

### 6) Segurança operacional

Princípios de falha segura:

- erro de inferência ML nunca bloqueia ciclo do BO;
- timeout de inferência com fallback automático;
- disable via feature flag sem restart complexo.

## Fluxo (Shadow)

1. Candle fechada -> BO avalia sinal.
2. Resultado BO segue fluxo normal atual.
3. Camada ML recebe contexto e calcula score.
4. Diagnóstico consolidado grava BO + ML.
5. Dashboard/API exibem comparação e rastreabilidade.

## Contratos de dados (alto nível)

### Diagnóstico de ciclo (adição)

- `ml_score: number | null`
- `ml_decision: "ALLOW" | "BLOCK" | "ABSTAIN" | null`
- `ml_reason: string | null`
- `ml_model_version: string | null`

### Assertividade comparativa (futuro próximo)

Permitir análise:

- baseline BO puro vs BO+ML-sugerido;
- impacto por símbolo/timeframe e período;
- delta de métricas (expectancy, drawdown, win rate).

## Plano de rollout técnico

1. Implementar estrutura de serviço ML com stub determinístico (sem modelo complexo).
2. Integrar em shadow mode e persistir diagnóstico.
3. Expor dados no dashboard-api para leitura comparativa.
4. Validar estabilidade de latência/erro.
5. Iniciar coleta de evidência para critérios Go/No-Go.

## Riscos e mitigação

- Overfitting inicial:
  - Mitigar com shadow e avaliação out-of-sample.
- Drift de regime:
  - Monitorar queda de performance e recalibração controlada.
- Complexidade operacional:
  - Feature flags + fallback garantido + métricas de saúde.

## Critério de pronto desta fase de design

- Arquitetura definida para shadow sem impacto real.
- Campos de diagnóstico ML especificados.
- Estratégia de rollout/rollback formalizada.
- Base pronta para gerar deltas de spec e tasks.
