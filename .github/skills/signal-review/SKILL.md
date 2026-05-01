---
name: signal-review
description: 'Workflow completo para revisar uma implementação de sinal ou indicador do Phicube contra o método BO Williams. Use quando precisar validar código de indicadores técnicos, condições de entrada/saída, cálculo de SL/TP, ou quando implementar qualquer mudança no signal_engine.py ou indicators.py.'
argument-hint: 'Módulo ou função a revisar (ex: signal_engine.py, indicators.py, evaluate())'
---

# Revisão de Sinal Phicube

Revisa uma implementação de sinal ou indicador técnico contra as regras do método BO Williams Phicube.

## Quando Usar

- Mudança em `src/strategy/indicators.py` ou `src/strategy/signal_engine.py`
- Nova condição de entrada ou saída proposta
- Suspeita de look-ahead bias ou erro numérico em indicador
- Antes de qualquer alteração no método ir para produção

## Procedimento

### 1. Ler o código relevante

Leia os módulos envolvidos:
- `src/strategy/indicators.py` — implementação do Alligator, AO e Fractais
- `src/strategy/signal_engine.py` — lógica de avaliação do sinal
- Testes em `tests/test_indicators.py` e `tests/test_signal_engine.py`

### 2. Verificar o Alligator (SMMA)

Confirme:
- [ ] SMMA usa a fórmula de Wilder: `smma[i] = (smma[i-1] * (period-1) + value[i]) / period`
- [ ] Jaw = SMMA(13) deslocado +8 períodos **à frente** (não para trás)
- [ ] Teeth = SMMA(8) deslocado +5 períodos à frente
- [ ] Lips = SMMA(5) deslocado +3 períodos à frente
- [ ] Condição bullish: `lips > teeth > jaw` **E** `close > lips, close > teeth, close > jaw`
- [ ] Condição bearish: inverso exato

### 3. Verificar o Awesome Oscillator (AO)

Confirme:
- [ ] Mediana calculada como `(high + low) / 2` — **não** sobre `close`
- [ ] AO = `SMA(mediana, 5) - SMA(mediana, 34)`
- [ ] Condição LONG: `AO > 0` na última vela fechada
- [ ] Condição SHORT: `AO < 0`

### 4. Verificar os Fractais de 5 barras

Confirme:
- [ ] Fractal de alta: `high[i] > high[i-1]` e `high[i] > high[i-2]` e `high[i] > high[i+1]` e `high[i] > high[i+2]`
- [ ] Unicidade: o `high` central deve ser **estritamente maior** (não igual) que os 4 vizinhos
- [ ] As **2 últimas linhas** do DataFrame são excluídas de `last_valid_fractal_high` e `last_valid_fractal_low`
- [ ] Busca retroativa de fractal válido com `lookback=100` por padrão
- [ ] Fractal inválido se a barra de referência coincide com o candle de entrada

### 5. Verificar a lógica do sinal

Confirme:
- [ ] O sinal avalia a **última vela fechada** — índice `[-2]` antes de descartar o último candle aberto
- [ ] O DataFrame recebe o último candle descartado antes de entrar no `evaluate()`
- [ ] LONG: alligator_bullish **E** AO > 0 **E** close > fractal_high
- [ ] SHORT: alligator_bearish **E** AO < 0 **E** close < fractal_low
- [ ] Stop loss LONG = `last_valid_fractal_low`
- [ ] Stop loss SHORT = `last_valid_fractal_high`
- [ ] Take profit = `entry ± (entry - SL) × risk_reward_ratio`

### 6. Verificar cobertura de testes

Confirme:
- [ ] Existe teste unitário para o indicador com valores numéricos conhecidos
- [ ] Existe teste de sinal LONG e SHORT válido
- [ ] Existe teste de sinal rejeitado (Alligator não bullish, AO negativo, sem fractal)
- [ ] Execute `pytest tests/test_indicators.py tests/test_signal_engine.py -v`

### 7. Consultar o Trader Sênior

Se qualquer item dos passos 2–5 falhar ou a mudança for substancial:
- Acione o agent `@trader-senior` com o trecho de código e o desvio identificado
- Aguarde aprovação explícita antes de avançar

## Critérios de Conclusão

- [ ] Todos os itens dos passos 2–5 confirmados
- [ ] Testes passando sem regressão
- [ ] Trader Sênior aprovou (se houve mudança no método)
