# SDD Stage 02 - Standardized Task

## Title

Implementação PhiCube com rollout seguro no `binance-phicube`

## Problem

As regras RN-PHI estão mapeadas em conhecimento, mas não operacionalizadas
integralmente no motor de decisão.

## Objective

Implementar pipeline PhiCube com decisão rastreável por regra e segurança
operacional.

## In Scope

- Plugin/engine PhiCube com estados e razões de decisão
- Modos `shadow`, `advisory`, `active` com feature flags
- Diagnóstico técnico operacional e observabilidade mínima
- Testes unitários, de contrato e de integração para gates

## Out of Scope

- Reengenharia completa do SignalEngine atual
- Inferência de fórmulas proprietárias não públicas
- Otimização além do necessário para estabilidade v1

## Success Criteria

- Regras RN-PHI v1 executáveis por contrato
- Promoção por gates formais com aprovação humana
- Rollback por flag sem regressão operacional

## Risks

- Ambiguidade residual de regra
- Falso positivo/negativo em classificações iniciais
- Acoplamento indevido com fluxos legados

## Status

Approved by human.
