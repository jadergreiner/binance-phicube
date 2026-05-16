## 1. Instrumentacao Diagnostica por Ciclo

- [x] 1.1 Mapear no runtime os pontos de emissao por etapa (`engine`, `risk`, `order`, `persist`) sem alterar semantica de trading.
- [x] 1.2 Adicionar evento estruturado por ciclo com campos minimos: `symbol`, `timeframe`, `candle_close_time`, `engine_outcome`, `risk_outcome`, `risk_reason`, `final_status`.
- [x] 1.3 Registrar classificacao deterministica do ciclo com valores `NO_SETUP_DETECTED`, `REJECTED_BY_RISK`, `PIPELINE_INTERRUPTED` e `PERSISTENCE_GAP`.

## 2. Evidencia de Rejeicao por Quantidade

- [x] 2.1 Capturar `qty_raw` e `qty_rounded` no fluxo de risco quando houver rejeicao por arredondamento.
- [x] 2.2 Persistir trilha de auditoria consultavel para casos `quantity_zero_after_rounding` com `risk_reason` e `final_status`.
- [x] 2.3 Garantir que a rejeicao por quantidade zero continue segura e sem abertura de posicao.

## 3. Deteccao de Ausencia Prolongada de Sinais

- [x] 3.1 Implementar regra de deteccao para distinguir ausencia legitima de setup de interrupcao tecnica do pipeline.
- [x] 3.2 Implementar deteccao de lacuna de persistencia quando houver decisao em runtime sem registro correspondente.
- [x] 3.3 Expor superficie consultavel por `symbol`/`timeframe` com classificacao consolidada e timestamp da ultima evidencia.

## 4. Testes

- [x] 4.1 Adicionar testes unitarios para classificacao dos cenarios `NO_SETUP_DETECTED` e `REJECTED_BY_RISK`.
- [x] 4.2 Adicionar testes para deteccao de `PIPELINE_INTERRUPTED` e `PERSISTENCE_GAP`.
- [x] 4.3 Adicionar testes para validacao do payload minimo de observabilidade por ciclo.

## 5. Validacao Final

- [x] 5.1 Executar `ruff check src/ tests/` e corrigir violacoes nos arquivos alterados.
- [x] 5.2 Executar testes focados do fluxo de sinal/risco/persistencia afetados pela instrumentacao.
- [x] 5.3 Executar `openspec validate --strict analise-de-sinais-gerados`.
