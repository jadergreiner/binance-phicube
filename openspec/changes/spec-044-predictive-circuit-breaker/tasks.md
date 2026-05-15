## 1. Configuracao e Contratos

- [x] 1.1 Adicionar configuracoes do predictive circuit breaker em `src/config/settings.py` (percentil, janela historica e tiers elegiveis) com defaults conservadores.
- [x] 1.2 Garantir leitura e injeção dessas configuracoes no fluxo de risco sem quebrar compatibilidade com configuracoes atuais.

## 2. Gate Preditiva no RiskManager

- [x] 2.1 Implementar metodo interno para avaliar `atr_ratio_atual` contra limiar percentil historico considerando tiers elegiveis.
- [x] 2.2 Integrar a gate preditiva em `RiskManager.calculate()` antes da aprovacao final de trade/position sizing.
- [x] 2.3 Implementar fallback seguro para dados invalidos ou historico insuficiente, sem bloquear trade apenas por erro de dado.
- [x] 2.4 Extrair criterio de bloqueio para uma Strategy dedicada, mantendo `RiskManager` como orquestrador.
- [x] 2.5 Organizar gates no formato Chain of Responsibility com ordem deterministica e short-circuit em rejeicao.

## 3. Observabilidade e Metricas

- [x] 3.1 Emitir evento estruturado `predictive_circuit_breaker_skipped` com campos minimos (symbol, tier, atr_ratio, threshold, reason).
- [x] 3.2 Expor contador agregado de skips preditivos na superficie de observabilidade consumida pelo dashboard.
- [x] 3.3 Implementar publicacao de evento no estilo Observer para desacoplar risco de transporte de telemetria.
- [x] 3.4 Criar Adapter de metricas para preservar contrato atual do dashboard ao incluir o novo contador.

## 4. Testes

- [x] 4.1 Criar testes unitarios cobrindo skip e nao-skip para tier elegivel acima/abaixo do limiar.
- [x] 4.2 Criar testes unitarios para tiers nao elegiveis e fallback de simbolo desconhecido.
- [x] 4.3 Criar testes para dados invalidos/insuficientes validando bypass seguro e continuidade do pipeline.
- [x] 4.4 Validar emissao do evento estruturado e contador agregado em testes de API/integracao relevantes.
- [x] 4.5 Cobrir testes de Strategy (criterio), Chain (ordem/short-circuit), Observer (publicacao) e Adapter (contrato do dashboard).

## 5. Validacao Final

- [x] 5.1 Executar `ruff check src/ tests/` e `ruff format src/ tests/` nos arquivos alterados.
- [x] 5.2 Executar testes focados do dominio de risco/dashboard e corrigir regressões.
- [x] 5.3 Executar `openspec validate --strict spec-044-predictive-circuit-breaker` garantindo conformidade da change.
