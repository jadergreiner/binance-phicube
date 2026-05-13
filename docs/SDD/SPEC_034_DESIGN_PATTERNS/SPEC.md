# SPEC_034 — Aplicação de Design Patterns no Phicube

## Status

DRAFT — Aguardando aprovação do Time A

## Objetivo

Aplicar design patterns estratégicos no codebase Phicube para melhorar:
- **Testabilidade**: componentes isolados e mockáveis
- **Manutenibilidade**: separação de concerns, redução de acoplamento
- **Segurança**: rollback automático, tratamento de erros tipado
- **Extensibilidade**: novos comportamentos sem modificar código existente

## Escopo

Esta SPEC cobre a aplicação de 5 design patterns prioritários identificados na sessão de refinamento do Time A (m0029).

## Padrões Priorizados

| # | Padrão | Módulo | Impacto | Esforço |
|---|--------|--------|---------|---------|
| 1 | **Builder** | `src/trading/trade_builder.py` | Alto | Médio |
| 2 | **Command** | `src/trading/commands/` | Alto | Alto |
| 3 | **Proxy** | `src/exchange/proxies/` | Médio | Baixo |
| 4 | **Pipeline** | `src/trading/tick_pipeline.py` | Alto | Alto |
| 5 | **Result** | `src/common/result.py` | Médio | Médio |

## Padrões Existentes (Manter)

- Template Method (`StrategyPlugin`)
- Chain of Responsibility (`SignalEngine`)
- Observer (`SignalEngine._observers`)
- Decorator (`PluginRegistry._wrap_plugin`)
- Registry (`PluginRegistry`)
- State (`RiskManager` circuit breaker)
- Facade (`RiskManager` ATR/slippage)
- Factory Method (`_create_notifier`)
- Strategy (`SizingMode`)

## Restrições

1. **Não quebrar compatibilidade retroativa** — `Trade`, `Signal`, `PositionSize` mantêm interfaces públicas
2. **Feature flag** — Pipeline do tick deve ser opt-in via config
3. **Cobertura mínima 80%** — cada subtask inclui testes
4. **Não alterar lógica de negócio** — apenas estrutura, não regras

## Critérios de Aceite

- [ ] `TradeBuilder` constrói `Trade` imutável com validação
- [ ] `Command` permite rollback automático de ordens em caso de falha
- [ ] `Proxy` reduz chamadas redundantes à exchange em ≥30%
- [ ] `Pipeline` processa tick com middlewares testáveis isoladamente
- [ ] `Result` tipa erros em `RiskManager.calculate()` e `OrderManager.execute()`
- [ ] Todos os testes passam (`pytest`)
- [ ] Lint passa (`ruff`)

## Dependências

- SPEC_033 (Plugin System) — concluída
- SPEC_043 (Circuit Breaker) — concluída

## Riscos

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| Refatoração Pipeline quebra tick | Alto | Feature flag, rollout gradual, testes de regressão |
| Command aumenta complexidade | Médio | Documentação clara, exemplos de uso |
| Result requer mudança em toda base | Médio | Aplicar incrementalmente, começar por RiskManager |

## Direcionamento Time B

Ver `task.json` e subtasks neste diretório.

---

## Histórico

- 2026-05-13: Criação após sessão Time A de refinamento (m0029)
