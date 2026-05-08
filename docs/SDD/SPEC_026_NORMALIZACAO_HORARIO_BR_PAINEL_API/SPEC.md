# SPEC_026 — Normalização de Horário Brasileiro no Painel e APIs

**ID:** SPEC_026  
**Status:** Concluída  
**Data:** 2026-05-08  
**Prioridade:** Alta

## 1. Objetivo

Padronizar a leitura operacional de horário em `America/Sao_Paulo` no painel e nas APIs do dashboard, mantendo persistência técnica em UTC no MongoDB.

## 2. Regras de Negócio

- Campos de timestamp legados em UTC/ISO devem permanecer no contrato para compatibilidade.
- Para cada timestamp exposto no escopo do painel, a API deve adicionar campo textual `*_br` no formato `DD/MM/YYYY HH:mm:ss`.
- Respostas com timestamps no escopo desta SPEC devem incluir `"timezone": "America/Sao_Paulo"`.
- Persistência no banco permanece em UTC, sem backfill/migração.

## 3. Escopo de Endpoints

- `GET /positions` e `WS /ws/positions`
- `GET /signals/history`
- `GET /trades/history`
- `GET /trades/open`
- `GET /health` e `GET /system/health` (health operacional)
- `GET /bot-activity`
- `GET /performance`
- `GET /performance/by-symbol`
- `GET /performance/by-timeframe`

## 4. Implementação

- Utilitário central: `src/api/datetime_utils.py`
  - `to_iso8601_utc(...)`
  - `to_brazil_datetime_str(...)`
  - `enrich_datetime_fields(...)`
- Rotas do dashboard ajustadas para serialização aditiva (`campo_utc` + `campo_utc_br`) e metadado `timezone`.
- Frontend ajustado para priorizar `*_br` e usar fallback legado quando ausente.

## 5. Critérios de Aceite

- [x] Endpoints do escopo retornam timestamps legados + `*_br` + `timezone`.
- [x] Formato `*_br` em `DD/MM/YYYY HH:mm:ss`.
- [x] Painel usa `*_br` sem depender de timezone local do navegador.
- [x] Compatibilidade preservada para consumidores que ainda usam campos UTC.
- [x] Sem alteração de comportamento de persistência UTC no MongoDB.
