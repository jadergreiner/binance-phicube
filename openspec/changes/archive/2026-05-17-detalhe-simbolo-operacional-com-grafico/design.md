# Design: detalhe-simbolo-operacional-com-grafico

## Visão Geral

Este design detalha a experiência operacional por símbolo com foco em clareza de decisão e segurança para escalar capital, mantendo implementação fora de escopo.

## Padrões de Design Adotados

Para reduzir acoplamento e aumentar consistência da especificação, este design adota:

1. **Facade**: visão unificada dos dados de detalhe por símbolo.
2. **State**: semáforo de risco com transições explícitas.
3. **Strategy**: avaliação de zonas operacionais por contexto.
4. **Factory Method**: explicação humana padronizada por classificação.
5. **Observer**: sincronização de blocos por eventos internos.

## Princípios de Design

1. Leitura rápida: usuário deve identificar em segundos o estado do símbolo.
2. Coerência: texto humano, gráfico e métricas devem contar a mesma história.
3. Segurança operacional: semáforo de risco sempre visível e prioritário.
4. Rastreabilidade: cada bloco com referência temporal (`as_of`, UTC).

## Escopo por Prioridade

### P0 (obrigatório)

- Home com todos os símbolos monitorados.
- Detalhe com blocos:
  - Snapshot
  - Última análise humana
  - Gráfico operacional com zonas
  - Histórico de trades
- Semáforo de risco por símbolo.
- Consistência temporal e numérica entre blocos.

### P1 (evolutivo)

- Filtros avançados e comparativos.
- Refinamentos visuais e de produtividade.
- Métricas adicionais de confiabilidade.

## Arquitetura de Informação

## Home

- Header: período, última atualização global.
- Controles: busca, filtro, ordenação.
- Lista de símbolos: cada item exibe resumo operacional.
- Ação principal: navegar para detalhe do símbolo.

## Detalhe do Símbolo

- Bloco 1: Snapshot atual.
- Bloco 2: Semáforo de risco.
- Bloco 3: Última análise humana.
- Bloco 4: Gráfico operacional com zonas e justificativas.
- Bloco 5: Histórico de trades.

## Componentes e Contratos

### Componente de Orquestração: `SymbolDetailFacade`

Responsabilidade:

- agregar payload de `snapshot`, `risk_status`, `last_analysis_human`, `chart`, `trades_history`
- garantir coerência de `symbol`, `timeframe`, `as_of`
- expor contrato único para a tela de detalhe

Contrato lógico mínimo:

- `symbol`
- `timeframe`
- `as_of`
- `snapshot`
- `risk`
- `last_analysis`
- `chart`
- `trades_history`

### 1) `RiskStatusBadge`

Campos:

- `risk_status`: `ok | atencao | bloqueado`
- `risk_flags[]`: lista de gatilhos ativos
- `as_of`: timestamp UTC

Modelo de estado (State Pattern):

- estados: `ok`, `atencao`, `bloqueado`
- transições válidas:
  - `ok -> atencao`
  - `atencao -> bloqueado`
  - `bloqueado -> atencao`
  - `atencao -> ok`
- `ok -> bloqueado` só permitido quando gatilho crítico for direto

### 2) `LastAnalysisHumanCard`

Campos obrigatórios:

- `what_i_saw`
- `what_i_decided`
- `why`
- `next_step`
- `full_text`
- `classification`
- `as_of`

Geração padronizada (Factory Method):

- entrada: `classification`, `risk_status`, `reason_code`
- saída: template humano consistente com campos obrigatórios
- fallback obrigatório para classificação desconhecida

Regras de linguagem:

- sem jargão técnico
- frases curtas
- máximo de 4 frases no resumo

### 3) `OperationalChartPanel`

Campos:

- `current_price`
- `candles[]`
- `levels.entry/sl/tp`
- `watch_zones[]`

`watch_zones[]` deve conter:

- `zone_id`
- `type`: `entrada | invalidacao | alvo | observacao`
- `price_min`, `price_max`
- `priority`: `high | medium | low`
- `why_human`
- `expected_action`

Avaliação por contexto (Strategy Pattern):

- estratégia selecionada por `timeframe` e `regime`
- a estratégia define `priority`, `expected_action` e severidade da zona
- saída mantém contrato único independente da estratégia

### 4) `TradesHistoryPanel`

Campos:

- `opened_at`, `closed_at`
- `side`
- `entry_price`, `exit_price`
- `quantity`
- `pnl_usdt`
- `status`, `close_reason`
- `as_of`

## Coerência Temporal e Numérica

Regras globais:

- Todos os blocos carregam `symbol`, `timeframe`, `as_of`.
- Preços e PnL devem informar unidade e precisão.
- Horário interno padrão: UTC (formatação local apenas na apresentação).

## Gatilhos de Risco (mínimo)

`bloqueado` quando houver pelo menos um:

- inconsistência de dados críticos
- falha recorrente de execução
- dados stale acima do limite operacional

`atencao` quando houver degradação parcial sem bloqueio total.

`ok` quando nenhum gatilho ativo.

Tabela de gatilhos e efeito de estado:

- `dados_criticos_inconsistentes` -> `bloqueado`
- `execucao_rejeitada_recorrente` -> `atencao` (e `bloqueado` se limiar crítico)
- `dados_stale_acima_limite` -> `atencao` (e `bloqueado` se persistente)

## Estados de UI

Por bloco:

- `loading`
- `empty`
- `partial_data`
- `error_recoverable`
- `stale_data`

Sincronização entre blocos (Observer Pattern):

- eventos internos mínimos:
  - `symbol_detail_updated`
  - `risk_status_changed`
  - `analysis_updated`
  - `chart_zones_updated`
  - `trades_history_updated`
  - `stale_state_detected`
- cada bloco assina apenas eventos necessários ao seu contexto

## Matriz de Template Humano

Mapeamento mínimo de `classification` para template:

- `SIGNAL_GENERATED` -> explica oportunidade encontrada + decisão de entrada + próximo passo
- `NO_SETUP_DETECTED` -> explica ausência de condição + decisão de espera + gatilho de revisão
- `REJECTED_*` -> explica bloqueio + motivo principal + condição para reavaliar
- `UNKNOWN` -> fallback neutro, sem jargão, com orientação de monitoramento

## Critérios de Aceite de Design

1. Home mostra 100% dos símbolos monitorados no recorte ativo.
2. Detalhe exibe todos os blocos P0 com `as_of` visível.
3. Toda zona do gráfico possui justificativa humana (`why_human`).
4. Última análise humana sempre presente no formato padronizado.
5. Semáforo de risco aparece de forma destacada no detalhe.
