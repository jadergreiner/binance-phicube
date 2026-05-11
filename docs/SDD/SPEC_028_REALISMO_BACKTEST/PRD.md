# PRD — Realismo em Backtest (SPEC_028)

**Documento:** Product Requirements Document
**Feature:** Realismo em Backtest — Slippage, Taxas e Sizing
**SPEC vinculada:** `SPEC_028_REALISMO_BACKTEST/SPEC.md` (v2.0)
**PRD raiz:** `PRD.md` § Fase 2 — "Backtests e walk-forward analysis"
**Data:** 2026-05-10
**Status:** Concluído

---

## Sumário Executivo

O backtest do Phicube hoje produz resultados **otimistas demais para serem confiáveis**: ignora slippage, taxas Binance e usa um cálculo de PnL linear que não reflete o tamanho real da posição. Isso leva o operador a tomar decisões baseadas em números que não se reproduzem na conta real.

Esta feature adiciona **3 camadas de realismo** ao motor de backtesting:

| Camada | Problema atual | Solução |
|--------|----------------|---------|
| **Slippage** | Entrada/saída no close exato do candle | Percentual por tier de liquidez do par (3 níveis) |
| **Taxas** | Zero custo de corretagem | Maker 0,02% / Taker 0,05% (padrão Binance VIP 0) |
| **Sizing** | PnL = `Δpreço × saldo ÷ entry` (erro de ~2x) | RiskManager real calcula tamanho de posição |

O resultado: o operador vê **Gross PnL** (sem custos, igual ao de hoje) lado a lado com **Net PnL** (com custos + sizing real). Comparação honesta. Decisão informada.

---

## Problema

### Cenário Atual

```python
# Como o backtest calcula PnL hoje (engine.py:162):
pnl = (exit_price - entry) * initial_balance / entry
```

Isso assume que **100% do saldo** está alocado em cada trade. O RiskManager real aloca tipicamente 0,5-2% por trade. Consequência:

| Métrica | Backtest atual | Realidade (aprox.) | Erro |
|---------|----------------|---------------------|------|
| PnL por trade (BTC, SL 2%) | +$100 | +$50 | **2x** |
| Drawdown (5 perdas) | -$500 | -$250 | **2x** |
| Impacto de taxas (0,05%) | $0 | $0,50/trade | **Infinito** |

### Dores do Operador

1. "O backtest mostra 40% de retorno, mas na conta real mal fiz 15%"
2. "Não sei quanto estou perdendo em taxas e slippage por trade"
3. "Ajusto parâmetros no backtest até o número ficar bonito — sem nenhum alerta de que estou fazendo data dredging"
4. "Não tenho histórico de quantas vezes rodei backtest no mesmo par para saber se estou otimizando demais"

---

## Proposta de Valor

| Para o operador | O que muda | Por que importa |
|-----------------|------------|-----------------|
| **Confiança nos resultados** | PnL reflete custos reais e tamanho de posição real | Decisões baseadas em números honestos |
| **Transparência** | Gross vs. Net lado a lado na mesma execução | Entende exatamente o impacto dos custos |
| **Proteção contra auto-engano** | Alertas informacionais (IC, degradação, multi-run) | Sabe quando o resultado não é estatisticamente significativo |
| **Auditabilidade** | Cada execução registrada em JSONL | Pode auditar quantas vezes ajustou parâmetros |
| **Análise de sensibilidade** | `--override-slippage` para cenários otimista/pessimista | Entende a margem de segurança da estratégia |

---

## Personas Impactadas

### Operador (primário)
- **Necessidade:** Saber se a estratégia é lucrativa no mundo real, não só no backtest
- **Ganha:** Resultado confiável que reflete a execução real na Binance
- **Perde se não fizermos:** Continua operando estratégias que só são lucrativas em backtest sem custos

### Desenvolvedor (secundário)
- **Necessidade:** Pipeline de backtest confiável para validar mudanças na estratégia
- **Ganha:** Métricas consistentes entre backtest e trades reais
- **Perde se não fizermos:** Dificuldade de validar se uma mudança no código realmente melhora o resultado

---

## Requisitos Funcionais

| ID | Requisito | Prioridade | Esforço | Satisfaz |
|----|-----------|------------|---------|----------|
| RF-01 | Slippage percentual automático por tier de liquidez do par | P0 | 1 dia | US-028-01 |
| RF-02 | Taxas maker/taker configuráveis com defaults Binance VIP 0 | P0 | 0,5 dia | US-028-01 |
| RF-03 | RiskManager integrado ao cálculo de PnL via flag `--realistic` | P0 | 1,5 dia | US-028-03 |
| RF-04 | Resultado Gross (sem custos) e Net (com custos) lado a lado | P0 | 0,5 dia | US-028-02 |
| RF-05 | Alerta informacional composto no CLI e API | P1 | 1 dia | US-028-04 |
| RF-06 | Logging automático de parâmetros em `backtest_runs.jsonl` | P1 | 0,5 dia | US-028-05 |
| RF-07 | Compatibilidade reversa: sem `--realistic`, engine = comportamento atual | P0 | 0 dia (built-in) | — |
| RF-08 | Override de slippage por parâmetro explícito com WARN no log | P1 | 0,5 dia | US-028-01 |

**Total estimado:** ~6-7 dias de implementação

---

## Requisitos Não-Funcionais

| ID | Requisito | Critério de Sucesso |
|----|-----------|---------------------|
| RNF-01 | Compatibilidade reversa | 100% dos testes SPEC_011 continuam passando sem alteração |
| RNF-02 | Performance | Backtest realista não adiciona mais que 5% de tempo vs. não-realista (mesmo N) |
| RNF-03 | Transparência | Gross PnL (SPEC_011) preservado como referência — operador sempre vê ambos |
| RNF-04 | Não-bloqueio | Alerta informacional nunca impede execução (exit code 0) |
| RNF-05 | Durabilidade do log | Falha de escrita em `backtest_runs.jsonl` nunca interrompe o backtest |

---

## Critérios de Sucesso

| Métrica | Como medir | Alvo |
|---------|------------|------|
| Precisão do PnL realista | Comparar 50 trades simulados vs. Testnet real | Erro < 10% do PnL real |
| Adoção do `--realistic` | % de execuções com flag ativa vs. total | > 80% após 1 mês |
| Alertando sem bloquear | Número de execuções bloqueadas = 0 | 0 bloqueios |
| Utilidade do alerta | % de execuções com alerts que levaram a ação corretiva | > 30% (média do mercado) |

---

## Riscos

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Operador ignora alerta informacional e opera estratégia frágil | Média | Alto (perda real) | Alerta visível, mas não bloqueia. Documentação educacional. |
| Slippage do tier não reflete a realidade do par | Média | Médio | Override explícito disponível. Tier map ajustável. |
| RiskManager no backtest tem bug diferente do RiskManager real | Baixa | Alto | Comparação periódica entre backtest e execução Testnet. |
| Operador abusa de `--override-slippage` para inflar resultados | Alta | Médio | WARN no log + alerta "override ativo" no output. |

---

## Stakeholders

| Papel | Envolvimento |
|-------|--------------|
| **Operador (você)** | Valida resultados, ajusta defaults de slippage, decide se adota `--realistic` como padrão |
| **Time B (execução)** | Implementa conforme SPEC v2.0 + Task Graph |
| **QA** | Valida TEST_028_01-11 + compatibilidade SPEC_011 |
| **Planner Agent** | Gera Task Graph a partir da SPEC refinada |

---

## Dependências

| Item | Depende de | Impacto se não resolvido |
|------|-----------|--------------------------|
| RiskManager no backtest | RiskManager existente (`src/trading/risk_manager.py`) | Bloqueante — sem isso, PnL realista não funciona |
| SPEC_011 (Motor de Backtesting) | Já implementada | Nenhum — SPEC_028 é extensão |
| Dados de liquidez por par | Tabela lookup (hard-coded na SPEC) | Configurável manualmente |

---

## Fora do Escopo (desta feature)

- **Slippage estocástico**: rejeitado no refinamento — impacto <0,3% do PnL, ROI negativo para MVP
- **Saldo virtual**: postergado — ideal, mas custo de implementação (dias) não justifica o ganho incremental no curto prazo
- **Spread observado via order book**: requer coleta de dados históricos — inviável para o MVP
- **Detector de overfitting automático**: depende do logging que estamos construindo agora — será SPEC futura
- **Gráfico de equity curve**: fora do escopo do backtest CLI/API atual

---

## Fluxo de Decisão

```
Operador roda backtest
       │
       ▼
── Sem --realistic ──→ Resultado Gross (compatível SPEC_011)
       │
── Com --realistic ──→ RiskManager calcula posição real
       │                ├── Slippage por tier do par
       │                ├── Taxa maker/taker por ordem
       │                ▼
       │         Resultado Net (com custos)
       │         + Gross (referência sem custos)
       │         + Alertas informacionais
       │         + Log em backtest_runs.jsonl
       │
       ▼
Operador compara Gross vs. Net
       │
       ├── Net > 0 e alertas verdes → Estratégia robusta
       ├── Net > 0 mas alerta amarelo → Precaução, considerar walk-forward
       └── Net < 0 → Estratégia não é lucrativa no mundo real
```

---

## Histórico

| Versão | Data | Autor | Mudanças |
|--------|------|-------|----------|
| 1.0 | 2026-05-10 | Time A (Refinamento) | Documento inicial pós-refinamento da SPEC_028 |
