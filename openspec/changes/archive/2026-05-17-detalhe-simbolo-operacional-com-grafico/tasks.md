# Tasks: detalhe-simbolo-operacional-com-grafico

- [ ] 1.0 Home de símbolos monitorados (P0)
- [ ] 1.1 Definir payload da home com 100% dos símbolos monitorados
- [ ] 1.2 Garantir campos obrigatórios por item (`symbol`, `timeframe`, `current_price`, `momentum_summary`, `last_analysis_summary`, `risk_status`, `period_pnl`, `as_of`)
- [ ] 1.3 Definir busca/filtro/ordenação (`symbol|pnl|momentum|status`)
- [ ] 1.4 Definir navegação de item para detalhe do símbolo

- [ ] 2.0 Snapshot operacional do símbolo (P0)
- [ ] 2.1 Definir contrato de snapshot (`symbol`, `timeframe`, `current_price`, short variation, `as_of`)
- [ ] 2.2 Definir regra temporal UTC no contrato

- [ ] 3.0 Facade de detalhe por símbolo (P0)
- [ ] 3.1 Definir contrato unificado de detalhe (`snapshot`, `risk`, `last_analysis`, `chart`, `trades_history`)
- [ ] 3.2 Definir coerência de `symbol`, `timeframe`, `as_of` entre sub-blocos

- [ ] 4.0 Semáforo de risco com máquina de estado (P0)
- [ ] 4.1 Definir contrato `risk_status` (`ok|atencao|bloqueado`) + `risk_flags[]` + `as_of`
- [ ] 4.2 Definir transições permitidas de estado
- [ ] 4.3 Definir regra para transição crítica direta para `bloqueado`
- [ ] 4.4 Definir política de rejeição/normalização de transições inválidas

- [ ] 5.0 Última análise humana padronizada (P0)
- [ ] 5.1 Definir contrato obrigatório (`classification`, `what_i_saw`, `what_i_decided`, `why`, `next_step`, `full_text`, `as_of`)
- [ ] 5.2 Definir regra de linguagem simples (sem jargão, resumo curto)
- [ ] 5.3 Definir limite de 4 frases no resumo
- [ ] 5.4 Definir mapeamento determinístico de template por `classification` (Factory Method)
- [ ] 5.5 Definir template de fallback para classificação desconhecida

- [ ] 6.0 Gráfico operacional com zonas observáveis (P0)
- [ ] 6.1 Definir payload de gráfico (`candles`, `current_price`, `levels.entry/sl/tp`, `watch_zones[]`, `as_of`)
- [ ] 6.2 Definir contrato mínimo de `watch_zones[]` (`zone_id`, `type`, `price_min`, `price_max`, `priority`, `why_human`, `expected_action`)
- [ ] 6.3 Fixar domínio de tipos (`entrada|invalidacao|alvo|observacao`)
- [ ] 6.4 Definir estratégia de avaliação de zonas por `timeframe` e regime (Strategy)

- [ ] 7.0 Histórico de trades do símbolo (P0)
- [ ] 7.1 Definir contrato de trade (`opened_at`, `closed_at`, `side`, `entry_price`, `exit_price`, `quantity`, `pnl_usdt`, `status`, `close_reason`, `as_of`)
- [ ] 7.2 Definir paginação e filtros por status/período

- [ ] 8.0 Coerência global de contratos (P0)
- [ ] 8.1 Definir unidade e precisão para preços, percentual e PnL
- [ ] 8.2 Definir coerência temporal global por `as_of`
- [ ] 8.3 Definir consistência de `symbol` e `timeframe` em todos os blocos

- [ ] 9.0 Estados de UI por bloco (P1)
- [ ] 9.1 Definir estado `loading`
- [ ] 9.2 Definir estado `empty`
- [ ] 9.3 Definir estado `partial_data`
- [ ] 9.4 Definir estado `error_recoverable`
- [ ] 9.5 Definir estado `stale_data`

- [ ] 10.0 Sincronização por eventos entre blocos (P1)
- [ ] 10.1 Definir eventos mínimos (`risk`, `analysis`, `chart`, `trades`) para atualização de blocos
- [ ] 10.2 Definir regra de atualização seletiva sem refresh completo (Observer)
- [ ] 10.3 Definir comportamento quando evento não afeta determinado bloco
