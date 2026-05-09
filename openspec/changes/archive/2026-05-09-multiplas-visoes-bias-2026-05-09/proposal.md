## Why

O painel hoje calcula apenas uma visão de bias baseada em balanço de exposição LONG vs SHORT. Isso responde "como o portfólio está alocado", mas não responde outras leituras úteis para decisão operacional (ex.: contribuição por PnL, concentração por símbolo e risco de desalinhamento entre visões).

Sem visões comparativas, o operador interpreta `NEUTRAL/low` como possível falha do sistema, quando na prática pode ser apenas efeito de carteira balanceada na métrica atual.

## What Changes

- Introduzir múltiplas visões de bias no snapshot do dashboard.
- Preservar a visão atual como baseline para backward compatibility.
- Expor racional e métricas intermediárias por visão para auditabilidade.
- Permitir comparação explícita entre visões no frontend.

## Capabilities

### New Capabilities
- `dashboard-market-bias`: cálculo e exposição de visões múltiplas de bias de mercado derivadas das posições abertas.

### Modified Capabilities
- `dashboard-market-bias`: visão "allocation" (atual) passa a coexistir com visões adicionais e metadados comparativos.

## Impact

- API do dashboard passa a incluir estrutura de comparação de bias.
- Frontend passa a exibir visões lado a lado (ou selecionáveis) com racional de cada visão.
- Operação ganha explicabilidade para status `NEUTRAL/low` e divergências entre métricas.
