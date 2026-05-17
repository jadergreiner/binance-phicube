# Project Knowledge - architecture.iniciar

## Scope

Project-specific architecture knowledge for `binance-phicube`.

## Current Technical Mapping

- Backend principal em `src/`.
- Frontend canônico servido em `http://127.0.0.1:8080/`.
- Fluxo de mudança e governança técnica usa OpenSpec (`openspec/`).

## Architectural Rules (Current Baseline)

- Mudanças devem seguir artefatos de especificação antes da execução.
- Validação técnica e testes de regressão são obrigatórios antes de
  fechamento de mudança.
- Ajustes em runtime/container devem ser verificados com evidência.

## Traceability

- Fonte inicial:
  - `README.md`
  - `AGENTS.md`
  - `openspec/`
