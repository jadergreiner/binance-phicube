## Why

O projeto mantém serialização manual repetitiva em múltiplas dataclasses, o que aumenta risco de inconsistência quando novos campos são adicionados. A padronização via protocolo e geração automática reduz boilerplate e melhora segurança de manutenção.

## What Changes

- Introduzir um protocolo comum de serialização com contrato explícito de `to_dict()`.
- Criar mecanismo automático para geração de `to_dict()` em dataclasses elegíveis, aplicando padrão `Decorator`.
- Refatorar dataclasses prioritárias para remover implementação manual duplicada, preservando compatibilidade de saída.
- Definir regras de serialização para campos aninhados, listas e dados sensíveis via política configurável (`Strategy`).
- Definir adaptação explícita para tipos não serializáveis nativamente (`Adapter`) quando necessário.
- Adicionar suíte de testes de conformidade para prevenir regressões de formato.

## Capabilities

### New Capabilities
- `serializable-protocol`: padronização e automação da serialização de dataclasses com contrato único de `to_dict`.

### Modified Capabilities
- Nenhuma.

## Impact

- Código afetado:
  - novo módulo comum em `src/common/`
  - `src/strategy/signal_engine.py`
  - `src/trading/risk_manager.py`
  - `src/trading/order_manager.py`
  - `src/backtest/models.py` (alvo opcional conforme escopo final)
- Testes afetados:
  - novos testes em `tests/common/`
  - ajustes/validações em testes dos módulos refatorados
- Risco principal:
  - quebra de compatibilidade de payload em `to_dict()` por diferença de chaves ou tipos.
