## Why

Esta change nasceu como rascunho no fluxo compat local e ficou sem requisitos executáveis. O objetivo agora é concluir formalmente este item sem perda de rastreabilidade, pois o escopo funcional foi implementado e fechado na change `intraday-loss-limit-10pct`.

## What Changes

- Formalizar que `ajuste-risco-intraday` não seguirá para implementação própria.
- Encerrar esta change como substituída por `intraday-loss-limit-10pct`.
- Evitar promoção de spec placeholder (`risk/spec.md`) no archive.

## Capabilities

### New Capabilities
- Nenhuma.

### Modified Capabilities
- `intraday-loss-guard`: esta change não altera requisitos; referencia a implementação já entregue em `intraday-loss-limit-10pct`.

## Impact

- Governança OpenSpec: encerramento limpo de change legada.
- Sem impacto adicional de código (mudança já implementada e arquivada em outra change).
