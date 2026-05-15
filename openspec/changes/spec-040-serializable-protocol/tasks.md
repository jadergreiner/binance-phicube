## 1. Fundação de serialização

- [x] 1.1 Criar `src/common/serialization.py` com contrato `Serializable` e
      mecanismo de geração automática de `to_dict()` para dataclasses
- [x] 1.2 Aplicar Strategy para política de serialização de campos (primitivo,
      aninhado, lista, sensível)
- [x] 1.3 Aplicar Adapter para normalizar objetos legados sem `to_dict()` no
      fluxo de serialização
- [x] 1.4 Aplicar Decorator para preservar `to_dict()` manual existente e
      adicionar comportamento sem sobrescrita destrutiva

## 2. Migração incremental de dataclasses

- [x] 2.1 Mapear e priorizar dataclasses alvo da primeira onda (Signal,
      SignalEvaluation, PositionSize, Trade)
- [ ] 2.2 Refatorar as dataclasses priorizadas para adoção do mecanismo
      padronizado removendo boilerplate repetitivo
- [ ] 2.3 Validar compatibilidade de payload para cada dataclass migrada
      comparando saída antiga vs nova de `to_dict()`
- [x] 2.4 Avaliar inclusão de dataclasses de backtest na mesma onda ou em fase
      posterior
- [x] 2.5 Introduzir Facade de serialização para uso único por camadas de
      trading, estratégia e persistência

## 3. Qualidade e validação

- [x] 3.1 Criar testes unitários de serialização automática (geração de campos,
      preservação de `to_dict()` manual, recursão, listas e erro em uso
      inválido)
- [ ] 3.2 Criar testes de paridade de formato serializado para dataclasses
      migradas
- [x] 3.3 Criar testes por padrão aplicado (Strategy, Adapter, Decorator,
      Facade) cobrindo fluxos nominal e erro
- [x] 3.4 Executar `pytest` no escopo afetado e corrigir regressões de
      serialização
- [ ] 3.5 Executar `ruff check src/ tests/` e `ruff format src/ tests/` no
      escopo alterado

## 4. Fechamento operacional da mudança

- [ ] 4.1 Atualizar documentação técnica relevante da mudança em
      `docs/SDD/SPEC_040_SERIALIZABLE_PROTOCOL/`
- [x] 4.2 Executar `openspec validate --strict spec-040-serializable-protocol`
      e garantir status válido do change
- [ ] 4.3 Consolidar evidências de teste e checklist de conclusão para revisão
      final
