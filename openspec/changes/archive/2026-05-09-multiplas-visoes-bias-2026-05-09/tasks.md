# Tasks

## 1. Especificacao
- [x] 1.1 Definir capability `dashboard-market-bias` com requisitos de visões múltiplas.
- [x] 1.2 Definir contrato de backward compatibility para `analysis.bias`.
- [x] 1.3 Definir critérios de divergência entre visões e texto explicativo.

## 2. Backend (futuro apply)
- [x] 2.1 Extrair cálculo atual para visão `allocation` explícita.
- [x] 2.2 Implementar visão `pnl_weighted`.
- [x] 2.3 Implementar visão `concentration`.
- [x] 2.4 Expor `analysis.bias_views` em `/positions` e `/ws/positions`.

## 3. Frontend (futuro apply)
- [x] 3.1 Exibir visão ativa e seletor de visões.
- [x] 3.2 Exibir racional/metrics por visão.
- [x] 3.3 Exibir alerta de divergência entre visões.

## 4. Validacao (futuro apply)
- [x] 4.1 Testes unitários de cada visão de bias.
- [x] 4.2 Testes de contrato da API para `analysis.bias_views`.
- [x] 4.3 Testes de renderização do comparativo no frontend.
- [x] 4.4 Rodar `pytest`, `ruff check .` e `ruff format .`.

## Evidencias Esperadas
- Snapshots com casos: carteira balanceada, bias direcional forte e divergência entre visões.
- Documentação de "como interpretar cada visão" no dashboard.
