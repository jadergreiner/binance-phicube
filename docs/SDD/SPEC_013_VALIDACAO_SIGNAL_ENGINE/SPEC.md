# SPEC_013 — Validação do Signal Engine: Curadoria, Corpus e Conformidade com o Método Phicube

**ID:** SPEC_013
**Status:** Concluída
**Data:** 2026-05-05
**Autor:** Time A (Refinamento)
**Executores:** Time B (Execução) — aguarda corpus anotado pelo operador
**Skills requeridas:** Python, pytest, pandas, structlog, conhecimento da estratégia BO Williams Phicube
**Depende de:** SPEC_001 (base do motor), corpus anotado pelo operador (dependência externa explícita)

---

## 1. Título e Resumo

### 1.1 Nome da Funcionalidade

Validação do Signal Engine — Curadoria, Corpus e Conformidade com o Método Phicube.

### 1.2 Resumo (High-Level Definition)

**O que é:** Suite de validação que garante que o `SignalEngine` detecta corretamente os setups Long e Short do método BO Williams Phicube. A validação opera sobre um corpus de casos anotados pelo operador (o próprio trader), com campos padronizados em JSON/CSV, e é executada como suite de testes parametrizados no CI.

**Por que estamos fazendo:** O `SignalEngine` existe e produz sinais, mas não existe nenhuma prova formal de que esses sinais estão corretos segundo o método. Qualquer divergência entre a lógica implementada e o método real representa risco financeiro direto. O operador é a única fonte de verdade sobre o que constitui um setup válido.

**Valor de negócio:** Elimina a possibilidade de o bot operar com lógica divergente do método sem que o operador saiba. Cria uma barreira de regressão: qualquer refatoração futura no `SignalEngine` que quebre um caso de setup real é detectada automaticamente.

**Conexão com PRD/SPEC:** PRD §Princípios — "todas as decisões de trading devem ser rastreáveis ao método"; MANIFESTO.md — método Phicube é âncora de todas as decisões de automação.

---

## 2. Objetivos e Escopo

### 2.1 Objetivos (o que será entregue)

- [ ] Especificação do formato canônico de anotação de corpus (JSON/CSV)
- [ ] Guia de curadoria para o operador: como identificar e anotar um setup válido
- [ ] Suite de testes parametrizados `tests/strategy/test_signal_engine_corpus.py`
- [ ] Relatório de conformidade gerado ao final da suite (passados, falhos, não cobertos)
- [ ] Documentação de gaps encontrados entre a implementação atual e o corpus

### 2.2 Fora do Escopo (Non-Goals)

- **Não inclui:** Modificação do `SignalEngine` — divergências são reportadas, não corrigidas nesta SPEC
- **Não inclui:** Backtesting com dados históricos de mercado (escopo da SPEC_011)
- **Não inclui:** Anotação automática de setups via ML (escopo futuro)
- **Não inclui:** Validação de indicadores individuais isoladamente (Alligator, AO, Fractals separados)
- **Não inclui:** Validação de risk sizing ou execução de ordens

---

## 3. Referências

| Documento | Seção | Relevância |
|---|---|---|
| `src/strategy/signal_engine.py` | `evaluate()` | Contrato de saída: `Long / Short / None` |
| `src/strategy/indicators.py` | todos | Implementação dos indicadores |
| `SPEC_011` | §5 | Formato de dados OHLCV utilizado no backtesting |
| `MANIFESTO.md` | §Método | Princípios do método Phicube |

---

## 4. Dependência Externa — Corpus Anotado pelo Operador

**Esta SPEC possui uma dependência de entrada bloqueante: o operador deve produzir e entregar o corpus anotado antes que o Time B possa implementar e executar os testes de conformidade.**

### 4.1 O que o Operador Deve Produzir

Um conjunto de no mínimo 20 casos de setup, sendo:

- Mínimo 8 setups Long confirmados
- Mínimo 8 setups Short confirmados
- Mínimo 4 casos negativos (candles onde o sinal correto é `None`, mesmo que indicadores estejam próximos de disparar)

### 4.2 Formato Canônico de Anotação — JSON

Cada caso de setup é um objeto JSON com a seguinte estrutura:

```json
{
  "case_id": "CASE_001",
  "symbol": "BTCUSDT",
  "timeframe": "5m",
  "date": "2025-03-15T14:30:00Z",
  "direction": "long",
  "fractal_ref": {
    "type": "low",
    "price": 82150.00,
    "bar_index": -3
  },
  "alligator_state": {
    "jaw_above_teeth": false,
    "teeth_above_lips": false,
    "lips_direction": "down_crossing_up",
    "description": "alligator acordando para cima — mandíbulas cruzando na direção do movimento"
  },
  "ao_value": {
    "current": 0.00045,
    "prev": -0.00012,
    "crossing_zero": true,
    "histogram_color": "green"
  },
  "expected_signal": "long",
  "notes": "Setup clássico de reversão no suporte — AO cruzando zero com alligator abrindo para cima após fractal de baixa confirmado"
}
```

### 4.3 Formato Alternativo — CSV

Para facilidade de edição em planilha, o mesmo corpus pode ser entregue em CSV com as colunas:

```
case_id, symbol, timeframe, date, direction, fractal_type, fractal_price,
fractal_bar_index, alligator_jaw_above_teeth, alligator_teeth_above_lips,
alligator_lips_direction, ao_current, ao_prev, ao_crossing_zero,
ao_histogram_color, expected_signal, notes
```

### 4.4 Critério de Qualidade do Corpus

- Cada caso deve ter `notes` preenchido com a justificativa do operador
- Casos negativos (`expected_signal: null`) devem indicar qual condição falhou
- Corpus deve cobrir pelo menos 3 símbolos diferentes e 2 timeframes diferentes
- O corpus é entregue como `docs/corpus/signal_corpus_v1.json` ou `.csv`

---

## 5. Requisitos Funcionais

| ID | Descrição | Prioridade |
|---|---|---|
| RF-001 | Suite lê corpus de `docs/corpus/signal_corpus_v1.json` ou `.csv` | Alta |
| RF-002 | Para cada caso, reconstrói o estado de indicadores a partir dos campos anotados | Alta |
| RF-003 | Chama `SignalEngine.evaluate()` com o estado reconstruído | Alta |
| RF-004 | Compara resultado com `expected_signal` do corpus | Alta |
| RF-005 | Gera relatório ao final: N passados, N falhos, taxa de conformidade | Alta |
| RF-006 | Falha de conformidade < 100% deve gerar warning no CI (não bloquear — é diagnóstico) | Média |
| RF-007 | Casos negativos (`expected_signal: null`) validam que nenhum sinal é gerado | Alta |
| RF-008 | Suite é parametrizada via `pytest.mark.parametrize` — um teste por caso | Alta |
| RF-009 | Relatório de gaps documenta divergências encontradas para correção futura no `SignalEngine` | Média |

---

## 6. Requisitos Não-Funcionais

| ID | Descrição |
|---|---|
| RNF-001 | Suite completa executa em menos de 30 segundos (dados já estão no corpus, sem I/O de mercado) |
| RNF-002 | Corpus versionado em git junto com o código |
| RNF-003 | Estrutura do corpus validada por schema (JSON Schema ou Pydantic) ao carregar |
| RNF-004 | Logs em structlog com level INFO por caso executado |
| RNF-005 | Compatível com `pytest` standalone — sem dependência de Binance ou MongoDB |

---

## 7. Cenários e Casos de Borda

| ID | Cenário | Comportamento Esperado |
|---|---|---|
| CE-001 | Corpus vazio ou ausente | Suite falha com erro descritivo antes de executar |
| CE-002 | Campo obrigatório ausente em caso do corpus | Schema validation falha com mensagem clara identificando o caso |
| CE-003 | `expected_signal` é `null` e `SignalEngine` retorna `Long` | Teste falha — divergência documentada no relatório |
| CE-004 | AO exatamente em zero (cruzamento no limite) | Caso deve ser anotado pelo operador com `notes` explicando o comportamento esperado |
| CE-005 | Mesmo setup em 2 timeframes diferentes com sinais opostos | Dois casos separados no corpus — cada um validado independentemente |
| CE-006 | Fractal confirmado mas Alligator ainda fechado | `expected_signal: null` — sinal não deve disparar |

---

## 8. Critérios de Aceite e DoD

### Critérios de Aceite

```text
DADO   que o corpus está presente em docs/corpus/signal_corpus_v1.json
QUANDO a suite tests/strategy/test_signal_engine_corpus.py é executada
ENTÃO  cada caso do corpus gera um teste parametrizado individual
E      o relatório final exibe: total, passados, falhos, taxa de conformidade
E      casos com expected_signal=null validam ausência de sinal
E      o CI executa a suite sem erros de infraestrutura
```

### Definição de Pronto (DoD)

- [ ] `docs/corpus/signal_corpus_v1.json` entregue pelo operador com mínimo 20 casos
- [ ] Schema de validação do corpus implementado (Pydantic ou JSON Schema)
- [ ] `tests/strategy/test_signal_engine_corpus.py` implementado com `pytest.mark.parametrize`
- [ ] Relatório de conformidade gerado ao final da execução
- [ ] Todos os casos passam OU divergências estão documentadas em `docs/corpus/gaps_v1.md`
- [ ] `docs/SDD/README.md` atualizado com SPEC_013
- [ ] `ruff check src/ tests/` sem erros

---

## 9. Decisões de Design

| ID | Decisão | Justificativa |
|---|---|---|
| DD-001 | Corpus anotado pelo operador (não gerado automaticamente) | O operador é a única fonte de verdade sobre o que é um setup válido no método Phicube |
| DD-002 | Corpus em JSON/CSV versionado em git | Rastreabilidade total de mudanças no corpus; diff legível |
| DD-003 | Suite diagnóstica (warning, não bloqueia CI em falha de conformidade) | Divergências devem ser investigadas, não suprimidas; bloquear CI forçaria ajuste do corpus ao invés de corrigir o engine |
| DD-004 | Reconstrução de estado por campos (não replay de candles) | Torna o corpus independente de dados de mercado externos; corpus é autocontido |
| DD-005 | Mínimo 20 casos com distribuição obrigatória | Menos que 20 casos não dá cobertura estatística suficiente para detectar regressões |

---

## 10. Riscos

| Risco | Impacto | Probabilidade | Mitigação |
|---|---|---|---|
| Operador não entrega corpus a tempo | Alto — bloqueia Time B completamente | Média | Time A define prazo com o operador antes de abrir a SPEC para execução |
| Corpus insuficiente (poucos casos negativos) | Alto — falsos positivos não são detectados | Média | Critério mínimo de 4 casos negativos é hard requirement |
| `SignalEngine` diverge do método em mais de 30% dos casos | Alto — risco financeiro real | Desconhecida até execução | Suite expõe divergências; operador decide se pausa operação até correção |
| Reconstrução de estado não captura todas as nuances do indicador | Médio — falsos passados na suite | Baixa | Casos de borda (CE-004, CE-006) devem ser incluídos no corpus |

---

## Histórico

- **2026-05-05:** Criação da SPEC_013 pelo Time A. Dependência de corpus anotado pelo operador declarada como bloqueante.
