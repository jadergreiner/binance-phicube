## 1. Contrato de Sinal Isolado

- [x] 1.1 Definir DTOs/estruturas imutáveis de entrada e saída do boundary de sinal em `src/strategy/`.
- [x] 1.2 Garantir mapeamento explícito de decisão (`LONG`, `SHORT`, ausência de sinal) no contrato isolado.

## 2. Adaptador e Integração no Runtime

- [x] 2.1 Implementar adaptador único para invocação do `SignalEngine` com validação mínima de entrada.
- [x] 2.2 Implementar normalização de retorno e tratamento de exceções no adaptador com fallback seguro.
- [x] 2.3 Integrar o adaptador no ponto de avaliação de sinal do orquestrador, removendo acoplamento direto.

## 3. Observabilidade e Compatibilidade

- [x] 3.1 Padronizar eventos de log do boundary/adaptador para sucesso, ausência de sinal e falha controlada.
- [x] 3.2 Verificar compatibilidade do contrato novo com os módulos de risco e ordem sem alterar semântica existente.

## 4. Testes Determinísticos

- [x] 4.1 Adicionar testes unitários do contrato isolado cobrindo entradas válidas e inválidas.
- [x] 4.2 Adicionar testes unitários do adaptador cobrindo normalização de `LONG`/`SHORT`/sem sinal.
- [x] 4.3 Adicionar teste de falha controlada garantindo que exceções do engine não interrompem o loop.

## 5. Validação Final

- [x] 5.1 Executar `ruff check src/ tests/` e corrigir violações.
- [x] 5.2 Executar `pytest tests/strategy -v` e testes de integração afetados pelo fluxo de sinal.
- [x] 5.3 Executar `openspec validate --strict spec-045-isolamento-signal-engine`.
