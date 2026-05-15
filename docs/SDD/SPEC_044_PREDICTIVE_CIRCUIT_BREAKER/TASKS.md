# TASKS — SPEC_044 Predictive Circuit Breaker

Status: DONE

## 1. Configuração e Contratos
- [x] 1.1 Adicionar configurações do predictive circuit breaker em `src/config/settings.py` (percentil, janela histórica e tiers elegíveis).
- [x] 1.2 Garantir leitura/injeção das configurações no fluxo de risco sem quebrar compatibilidade.

## 2. Gate Preditiva no RiskManager
- [x] 2.1 Implementar método interno para avaliar `atr_ratio_atual` contra limiar percentil histórico por tiers elegíveis.
- [x] 2.2 Integrar gate preditiva em `RiskManager.calculate()` antes da aprovação final de trade.
- [x] 2.3 Implementar fallback seguro para dados inválidos ou histórico insuficiente.
- [x] 2.4 Extrair critério de bloqueio para Strategy dedicada.
- [x] 2.5 Organizar gates no formato chain com ordem determinística e short-circuit.

## 3. Observabilidade e Métricas
- [x] 3.1 Emitir evento estruturado `predictive_circuit_breaker_skipped`.
- [x] 3.2 Expor contador agregado de skips preditivos para consumo do dashboard/health.
- [x] 3.3 Publicar evento desacoplado da decisão de risco (observer boundary).
- [x] 3.4 Preservar contrato de consumo com adaptação no endpoint de health.

## 4. Testes
- [x] 4.1 Cobrir skip e não-skip para tier elegível acima/abaixo do limiar.
- [x] 4.2 Cobrir tiers não elegíveis e fallback de símbolo/tier.
- [x] 4.3 Cobrir dados inválidos/insuficientes com bypass seguro.
- [x] 4.4 Validar evento estruturado e contador agregado em testes de API/integrados.
- [x] 4.5 Cobrir Strategy/Chain/Observer/Adapter no escopo funcional validado.

## 5. Validação Final
- [x] 5.1 Executar lint/formatação dos arquivos alterados.
- [x] 5.2 Executar testes focados de risco e dashboard.
- [x] 5.3 Executar `openspec validate --strict spec-044-predictive-circuit-breaker`.
