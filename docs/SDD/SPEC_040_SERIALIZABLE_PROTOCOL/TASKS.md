## SPEC_040 - Tasks

## 1. Fundação de serialização

- [x] 1.1 Criar `src/common/serialization.py` com contrato `Serializable`
- [x] 1.2 Aplicar Strategy para política de serialização de campos
- [x] 1.3 Aplicar Adapter para normalização de objetos legados
- [x] 1.4 Aplicar Decorator para preservar `to_dict()` manual existente

## 2. Migração incremental de dataclasses

- [x] 2.1 Mapear e priorizar dataclasses da primeira onda
- [x] 2.2 Refatorar dataclasses priorizadas para mecanismo padronizado
- [x] 2.3 Validar compatibilidade de payload antes/depois da migração
- [x] 2.4 Avaliar inclusão de dataclasses de backtest
- [x] 2.5 Introduzir Facade de serialização para camadas consumidoras

## 3. Qualidade e validação

- [x] 3.1 Criar testes unitários de serialização automática
- [x] 3.2 Criar testes de paridade de formato serializado
- [x] 3.3 Criar testes por padrão aplicado (Strategy/Adapter/Decorator/Facade)
- [x] 3.4 Executar `pytest` no escopo afetado
- [x] 3.5 Executar `ruff check` e `ruff format` no escopo alterado

## 4. Fechamento operacional

- [x] 4.1 Atualizar documentação técnica da mudança
- [x] 4.2 Executar `openspec validate --strict spec-040-serializable-protocol`
- [x] 4.3 Consolidar evidências de testes e checklist final
