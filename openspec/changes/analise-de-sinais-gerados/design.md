## Context

No ambiente atual do bot, o último sinal registrado foi em **13/05/2026 11:31:05** para `PLTRUSDT` (`15m`, `SHORT`), com rejeição por risco (`REJECTED_RISK_QTY_ZERO`, `quantity_zero_after_rounding`). Após esse evento, não foram observados novos sinais processados.

O fluxo de decisão e execução atravessa múltiplos módulos (`SignalEngine`, orquestração do monitor, `RiskManager`, persistência em Mongo e observabilidade). A ausência de novos sinais pode ser causada por:

- ausência legítima de setups da estratégia;
- rejeição contínua em gates de risco;
- interrupção no loop de monitoramento/candle close;
- falha silenciosa de persistência/telemetria mascarando atividade real.

Como o problema é transversal, o design precisa padronizar diagnóstico com evidências objetivas e pontos de instrumentação mínimos.

## Goals / Non-Goals

**Goals:**
- Tornar determinístico o diagnóstico de “último sinal conhecido e ausência de novos sinais”.
- Isolar em qual etapa ocorre o bloqueio: geração (`SignalEngine`), risco/quantidade, execução ou persistência.
- Definir trilha de auditoria mínima para cada ciclo de avaliação por símbolo/timeframe.
- Permitir correção incremental sem alterar semântica de trading quando o comportamento atual estiver correto.

**Non-Goals:**
- Redesenhar a estratégia BO Williams.
- Alterar critérios de entrada/saída sem evidência de bug.
- Reescrever arquitetura do monitor além do necessário para rastreabilidade.
- Introduzir dependências externas novas para observabilidade.

## Decisions

### 1) Introduzir diagnóstico por estágios no ciclo de sinal
**Decisão:** instrumentar o ciclo com resultado explícito por estágio (`engine`, `risk`, `order`, `persist`) e motivo padronizado.

**Racional:** o status final atual (`REJECTED_RISK_QTY_ZERO`) não garante visibilidade contínua após o último evento. A separação por estágio permite identificar “não houve sinal”, “houve sinal e risco rejeitou”, ou “houve execução sem persistência”.

**Alternativas consideradas:**
- Apenas aumentar logs textuais: descartado por baixa consultabilidade e pouca consistência.
- Diagnóstico apenas via testes: descartado pois não cobre estado operacional real.

### 2) Definir contrato de evidência operacional mínima por ciclo
**Decisão:** registrar, por ciclo, campos mínimos: `symbol`, `timeframe`, `candle_close_time`, `engine_outcome`, `risk_outcome`, `risk_reason`, `qty_raw`, `qty_rounded`, `final_status`.

**Racional:** o caso `quantity_zero_after_rounding` depende de contexto numérico para distinguir erro de regra esperada.

**Alternativas consideradas:**
- Persistir payload completo de cada módulo: descartado por custo/ruído e potencial exposição indevida.
- Manter apenas status final: descartado por insuficiência diagnóstica.

### 3) Aplicar classificação determinística para ausência de sinais
**Decisão:** classificar períodos sem novos sinais em categorias mutuamente exclusivas:
- `NO_SETUP_DETECTED`
- `REJECTED_BY_RISK`
- `PIPELINE_INTERRUPTED`
- `PERSISTENCE_GAP`

**Racional:** elimina ambiguidade entre “mercado sem setup” e falha operacional.

**Alternativas consideradas:**
- Categoria única “NO_SIGNAL”: descartado por não separar saúde técnica de decisão estratégica.

### 4) Implementar investigação com escopo controlado antes de qualquer mudança de regra
**Decisão:** primeiro fasear em “coletar evidências + validar hipótese”, só depois aplicar correções.

**Racional:** evita regressão ao ajustar risk/rounding sem comprovação de defeito.

**Alternativas consideradas:**
- Corrigir diretamente arredondamento/threshold: descartado por risco de mascarar causa-raiz.

## Risks / Trade-offs

- **[Risco]** Aumento de logs pode gerar ruído operacional  
  **Mitigação:** padronizar campos e níveis, com foco em eventos de decisão.

- **[Risco]** Diagnóstico apontar comportamento “esperado” sem bug de código  
  **Mitigação:** produzir evidência objetiva e recomendar ajuste de parâmetros operacionais/documentação.

- **[Risco]** Mudanças em instrumentação afetarem performance do loop  
  **Mitigação:** payload enxuto, sem serializações pesadas, e medições em testes focados.

- **[Risco]** Conclusão incorreta por janela de análise curta  
  **Mitigação:** definir janela mínima por símbolo/timeframe e cruzar com dados de candle e auditoria.

## Migration Plan

1. Adicionar instrumentação diagnóstica mínima no pipeline de avaliação por ciclo.
2. Cobrir com testes unitários/integrados os cenários de classificação (`NO_SETUP_DETECTED`, `REJECTED_BY_RISK`, etc.).
3. Executar validação em ambiente local com replay/janela recente de `PLTRUSDT 15m`.
4. Se a causa for bug, aplicar correção pontual e manter compatibilidade com contratos atuais.
5. Se a causa for comportamento esperado, formalizar recomendação operacional (ex.: parâmetros de risco/precisão).
6. Validar com `openspec validate --strict` antes de fechamento da change.

**Rollback:** por se tratar de observabilidade e diagnóstico incremental, rollback é reversão simples dos pontos de instrumentação caso haja impacto.

## Open Questions

- O par `PLTRUSDT` possui restrições de precisão/lot size recentes que aumentaram incidência de `qty=0` após arredondamento?
- O status “sem novos sinais” foi observado apenas em persistência (`signals`) ou também em `audit`/logs de runtime?
- Há política desejada para quando `qty_rounded == 0` (ex.: recalcular com piso mínimo permitido vs. rejeitar)?
- Qual janela temporal mínima deve ser considerada para concluir “pipeline interrompido”?
