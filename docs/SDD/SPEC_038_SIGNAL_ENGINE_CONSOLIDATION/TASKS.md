# Tasks

As tasks abaixo foram executadas como entregáveis independentes e verificáveis. Cada item registra uma saída específica e, quando aplicável, a dependência imediata que o precede.

## Active

## Waiting On

- [ ] **Decisão sobre atualização da SPEC_013** - alinhar se a SPEC de validação do corpus deve citar `WilliamsStrategy` explicitamente como implementação concreta do método BO Williams.
  - Relacionada a uma eventual revisão da SPEC_013.

## Someday

- [ ] **Abrir SPEC futura para metadata pública de diagnóstico** - caso o time decida expor o diagnóstico fora de logs/estrutura interna.

## Done

- [x] ~~**Task 1 - Fixar o escopo da SPEC** - saída: alvo funcional consolidado em `src/strategies/williams_strategy.py` e `SignalEngine` preservado; dependência: nenhuma.~~ (2026-05-15)
- [x] ~~**Task 2 - Especificar o contrato de parâmetros por direção** - saída: contrato interno imutável para LONG/SHORT sem TP; dependência: Task 1.~~ (2026-05-15)
- [x] ~~**Task 3 - Especificar o fluxo consolidado de avaliação** - saída: sequência única de avaliação com prioridade LONG -> SHORT; dependência: Task 2.~~ (2026-05-15)
- [x] ~~**Task 4 - Especificar a política de diagnóstico** - saída: diagnóstico apenas interno, via logs estruturados ou apoio privado; dependência: Task 3.~~ (2026-05-15)
- [x] ~~**Task 5 - Especificar invariantes e regras de negócio** - saída: regras de SL/TP, prioridade e compatibilidade com `SignalResult`; dependência: Task 3.~~ (2026-05-15)
- [x] ~~**Task 6 - Especificar a matriz de validação** - saída: checklist de testes, corpus SPEC_013 e não regressão; dependência: Task 5.~~ (2026-05-15)
