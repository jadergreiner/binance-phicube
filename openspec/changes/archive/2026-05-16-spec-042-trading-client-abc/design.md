## Context

A camada de exchange possui dois clientes (`BinanceClient` e `SimulatedBinanceClient`) usados por componentes críticos (`OrderManager`, `RuntimeMonitorRegistry`, `OrderMonitor`) sem contrato formal compartilhado, com tipagem `Any` em pontos centrais. Isso reduz segurança de integração, dificulta evolução para novos provedores e atrasa detecção de incompatibilidades.

Stakeholders principais: engenharia de trading, manutenção operacional e qualidade (CI/type-check).

Restrições: manter comportamento funcional atual, não alterar lógica de execução de ordens, preservar compatibilidade com modo simulação e testnet.

## Goals / Non-Goals

**Goals:**
- Formalizar um contrato `TradingClient` para operações de exchange.
- Padronizar assinaturas obrigatórias para mercado, ordens, posições, precisão e ciclo de vida.
- Eliminar `Any` em consumidores críticos substituindo por `TradingClient`.
- Viabilizar evolução segura para novos clientes de exchange sem acoplamento adicional.

**Non-Goals:**
- Implementar nova exchange.
- Alterar regras de estratégia, risco ou execução de ordens.
- Reescrever a lógica interna de simulação além do necessário para aderência ao contrato.

## Decisions

1. **Adotar ABC como contrato principal (`TradingClient`)**
Racional: em Python, `ABC + abstractmethod` fornece validação estrutural no momento de instanciação e melhora legibilidade de contrato.
Alternativas:
- `Protocol` puro: melhor para duck typing, porém menor pressão em runtime para implementação completa.
- Manter `Any`: descartado por falta de segurança estática.

2. **Aplicar padrões de design de forma explícita**
- **Strategy**: consumidores recebem `TradingClient` e podem alternar estratégia concreta (`BinanceClient` vs `SimulatedBinanceClient`) sem mudança de comportamento do consumidor.
- **Adapter**: cada cliente concreto adapta sua API interna (CCXT real ou simulação local) para o mesmo contrato.
- **Facade (dependência de contrato)**: `OrderManager` e registries passam a depender de uma superfície única simplificada (`TradingClient`), reduzindo espalhamento de detalhes concretos.
- **Template Method parcial no ABC**: métodos opcionais com default (`validate_market_liquidity`, `fetch_quantity_precision_map`) definem fluxo-base com especialização opcional.

3. **Tipagem forte nos consumidores críticos**
Racional: substituir `Any` por `TradingClient` em construtores críticos remove classe inteira de erros de integração e facilita revisão de mudanças.
Alternativas:
- Union de tipos concretos: cria acoplamento explícito aos clientes atuais e piora extensibilidade.

4. **Sem breaking externo**
Racional: mudança é interna de arquitetura e tipagem; endpoints e comportamento operacional permanecem estáveis.

## Risks / Trade-offs

- [Risco] Cliente concreto não implementar algum método obrigatório → **Mitigação**: validação imediata por `ABC`, testes de instanciação e execução de suíte de exchange.
- [Risco] Divergência semântica entre real e simulado em métodos comuns → **Mitigação**: requisitos normativos na spec + cenários para ambos clientes.
- [Trade-off] Maior rigor de contrato aumenta esforço inicial de manutenção → **Mitigação**: ganhos de previsibilidade e extensibilidade superam custo incremental.
- [Risco] Mudanças de assinatura propagarem erro em runtime tardio → **Mitigação**: tipagem em consumidores + validação strict no OpenSpec + testes.

## Migration Plan

1. Criar `src/exchange/base_client.py` com `TradingClient`.
2. Ajustar `BinanceClient` para herdar e aderir ao contrato.
3. Ajustar `SimulatedBinanceClient` para herdar e aderir ao contrato.
4. Refatorar tipagens de `OrderManager`, `RuntimeMonitorRegistry` e `OrderMonitor`.
5. Rodar lint, testes e validação OpenSpec strict.
6. Rollback (se necessário): reverter change mantendo clientes concretos como estavam, sem mudança de dados persistidos.

## Open Questions

- O projeto adotará `mypy`, `pyright` ou ambos como gate formal para tipagem de contrato?
- Métodos hoje retornando `dict[str, Any]` devem evoluir para DTOs tipados em SPEC futura?
