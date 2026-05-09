## Context

Atualmente, `build_market_analysis` usa apenas exposição agregada LONG vs SHORT para definir direção, confiança e razão textual. Essa abordagem é simples e estável, porém limitada: duas carteiras com riscos distintos podem receber o mesmo `NEUTRAL/low` quando o net exposure é pequeno.

## Goals / Non-Goals

**Goals:**
- Definir contrato de dados para múltiplas visões de bias no endpoint de posições.
- Garantir explicabilidade com métricas de suporte por visão.
- Manter compatibilidade com consumidores que usam o campo de bias atual.

**Non-Goals:**
- Alterar lógica de execução de trades do bot.
- Definir estratégia quantitativa "correta" universal; foco é comparação operacional.

## Candidate Views

1. Allocation Bias (baseline)
- Base: diferença relativa entre exposições LONG e SHORT.
- Objetivo: mostrar orientação líquida da alocação atual.

2. PnL-Weighted Bias
- Base: soma de PnL não realizado por lado, normalizada por exposição do lado.
- Objetivo: capturar qual lado está performando melhor no momento.

3. Concentration Bias
- Base: concentração por símbolo/lado (top exposure share).
- Objetivo: evidenciar risco de concentração mesmo com net exposure neutro.

## Data Contract Sketch

```json
{
  "analysis": {
    "bias": { "direction": "NEUTRAL", "confidence": "low", "score": 0.02, "reason": "..." },
    "bias_views": {
      "active": "allocation",
      "views": [
        {
          "id": "allocation",
          "direction": "NEUTRAL",
          "confidence": "low",
          "score": 0.02,
          "reason": "...",
          "metrics": { "long_exposure": 503.16, "short_exposure": 531.41, "relative_balance": 0.027 }
        },
        {
          "id": "pnl_weighted",
          "direction": "LONG",
          "confidence": "medium",
          "score": 0.34,
          "reason": "...",
          "metrics": { "long_pnl": 42.1, "short_pnl": -18.3 }
        },
        {
          "id": "concentration",
          "direction": "SHORT",
          "confidence": "low",
          "score": 0.18,
          "reason": "...",
          "metrics": { "top_symbol": "ETHUSDT", "top_share": 0.18 }
        }
      ],
      "divergence": {
        "has_divergence": true,
        "summary": "allocation=NEUTRAL while pnl_weighted=LONG"
      }
    }
  }
}
```

## Decisions

- Decisão 1: manter `analysis.bias` como visão padrão (`allocation`) por compatibilidade.
- Decisão 2: adicionar `analysis.bias_views` para comparação estruturada.
- Decisão 3: cada visão MUST expor `metrics` mínimas para auditoria do racional.

## Risks / Trade-offs

- [Risco] Sobrecarga cognitiva no frontend com muitas métricas.
  -> Mitigação: default simples + drill-down opcional.
- [Risco] Divergência frequente entre visões gerar dúvida operacional.
  -> Mitigação: bloco explicativo de divergência e "quando usar" cada visão.
- [Trade-off] Maior payload e custo de manutenção analítica.
  -> Mitigação: versões iniciais com 2-3 visões de baixo custo computacional.

## Done When

- Change contém proposal, design, tasks e delta de spec aprováveis.
- Requisitos declaram contrato mínimo de `bias_views` e compatibilidade com `analysis.bias` legado.
- Cenários cobrem neutral persistente e divergência entre visões.
