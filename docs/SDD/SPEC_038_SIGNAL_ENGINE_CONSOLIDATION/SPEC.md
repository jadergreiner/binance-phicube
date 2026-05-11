# SPEC_038 — Consolidação do SignalEngine (LONG/SHORT)

**ID:** SPEC_038
**Status:** Rascunho
**Data:** 2026-05-11
**Versão:** 1.0
**Dependências:** SPEC_037 (padrão de refatoração)
**Skill de validação:** `signal-review`, `sdd-spec-driven-development`, `qa-review`

---

## 1. Título e Resumo

### 1.1 Nome da Funcionalidade

Consolidação da lógica de avaliação LONG/SHORT no `SignalEngine`

### 1.2 Resumo

**O que é:** Refatoração do `SignalEngine.evaluate()` para eliminar a duplicação quase total entre os blocos LONG e SHORT (~180 linhas de código simétrico), substituindo por uma abordagem orientada a dados com parâmetros de direção.

**Por que estamos fazendo:** O método `evaluate()` em `signal_engine.py` tem dois blocos de ~90 linhas cada que diferem apenas nos nomes das condições (bullish/bearish), nos sinais de comparação e no cálculo do take profit. Qualquer bug corrigido em um lado precisa ser replicado manualmente no outro — fonte conhecida de regressão.

**Valor de negócio:** Reduz ~120 linhas de código (60% do bloco de avaliação), elimina duplicação, garante que correções em LONG se apliquem automaticamente a SHORT, facilita adição de novas direções se necessário.

**Conexão com PRD/SPEC:** Refatoração técnica do módulo `src/strategy/signal_engine.py` — sem mudança de comportamento.

---

## 2. Objetivos e Escopo

### 2.1 Objetivos

- [ ] Extrair lógica de avaliação de direção para método `_evaluate_direction(direction, enriched) -> Signal | None`
- [ ] Long e Short usam o mesmo código com parâmetros de direção invertidos
- [ ] `SignalEvaluation` preserva ambas as condições (long_conditions e short_conditions)
- [ ] Zero mudança de comportamento — todos os testes existentes passam sem alteração

### 2.2 Fora do Escopo

- **Não inclui:** Mudança na lógica de detecção de fractais ou alligator
- **Não inclui:** Adição de novas direções (ex: neutral)
- **Não inclui:** Mudança no formato de log ou SignalEvaluation.to_dict()

---

## 3. Referências

| Documento | Seção | Relevância |
|---|---|---|
| `src/strategy/signal_engine.py` | `evaluate()` (linhas 129-313) | Código alvo da refatoração |
| `docs/SDD/SPEC.md` | §3 | Contrato do motor de sinais |
| `SPEC_013/SPEC.md` | — | Validação do SignalEngine |

---

## 4. Histórias de Usuário e Requisitos

### US-038-01: Extração de `_evaluate_direction`

> Como **desenvolvedor**, quero **um único método que avalia LONG ou SHORT com base em parâmetros de direção** para **eliminar a duplicação de código**.

**Critérios de Aceitação:**

```text
DADO   um SignalEngine
QUANDO _evaluate_direction(Direction.LONG, enriched) é chamado
ENTÃO  retorna Signal com direction=LONG se condições LONG forem satisfeitas
```

```text
DADO   um SignalEngine
QUANDO _evaluate_direction(Direction.SHORT, enriched) é chamado
ENTÃO  retorna Signal com direction=SHORT se condições SHORT forem satisfeitas
```

```text
DADO   um SignalEngine avaliando direções
QUANDO nenhuma direção tem condições satisfeitas
ENTÃO  SignalEvaluation contém ambas long_conditions e short_conditions
```

- [ ] AC-01: `_evaluate_direction` aceita `Direction` e retorna `Signal | None`
- [ ] AC-02: O log `long_conditions_check` / `short_conditions_check` é preservado
- [ ] AC-03: Testes existentes passam sem modificação

### US-038-02: Contrato de parâmetros por direção

> Como **desenvolvedor**, quero **um dicionário ou dataclass que mapeie os parâmetros de cada direção** para **garantir simetria e facilitar manutenção**.

**Exemplo de design:**

```python
@dataclass(frozen=True)
class _DirectionParams:
    alligator_check: Callable[[float, float, float, float], bool]
    ao_condition: Callable[[float], bool]
    fractal_ref: Callable[[pd.DataFrame], float | None]
    close_condition: Callable[[float, float], bool]
    sl_func: Callable[[pd.DataFrame], float | None]
    sl_valid_check: Callable[[float, float], bool]
    tp_formula: Callable[[float, float, float], float]
    log_event: str
```

- [ ] AC-01: DirectionParams contém 1 função de alligator, 1 de AO, 1 de fractal, 1 de preço, 1 de SL, 1 de TP

---

## 5. Design e Arquitetura

### 5.1 Interface Pública Atual (inalterada)

```python
def evaluate(
    self,
    symbol: str,
    timeframe: str,
    df: pd.DataFrame,
) -> Signal | None:
    """Assinatura inalterada — compatibilidade total."""
```

### 5.2 Nova Estrutura Interna

```python
def evaluate(self, symbol: str, timeframe: str, df: pd.DataFrame) -> Signal | None:
    # ... validações iniciais inalteradas ...

    for direction, params in self._direction_params().items():
        signal = self._evaluate_direction(symbol, timeframe, direction, params, enriched, last)
        if signal is not None:
            return signal

    # ... SignalEvaluation com ambas as condições ...
    return None


def _direction_params(self) -> dict[Direction, _DirectionParams]:
    """Retorna parâmetros simétricos para LONG e SHORT."""
    return {
        Direction.LONG: _DirectionParams(
            alligator_check=self._is_alligator_bullish,
            ao_check=lambda ao: ao > 0,
            fractal_ref=lambda df: last_valid_fractal_high(df),
            close_condition=lambda close, ref: close > ref,
            sl_func=lambda df: last_valid_fractal_low(df),
            sl_valid=lambda close, sl: sl < close,
            tp_formula=lambda close, sl, rrr: close + (close - sl) * rrr,
            log_event="long_conditions_check",
        ),
        Direction.SHORT: _DirectionParams(
            alligator_check=self._is_alligator_bearish,
            ao_check=lambda ao: ao < 0,
            fractal_ref=lambda df: last_valid_fractal_low(df),
            close_condition=lambda close, ref: close < ref,
            sl_func=lambda df: last_valid_fractal_high(df),
            sl_valid=lambda close, sl: sl > close,
            tp_formula=lambda close, sl, rrr: close - (sl - close) * rrr,
            log_event="short_conditions_check",
        ),
    }
```

### 5.3 Fluxo de Dados

```mermaid
flowchart TD
    A[evaluate()] --> B{len(df) < 50?}
    B -->|Sim| C[return None]
    B -->|Não| D[compute_all indicators]
    D --> E[Loop: LONG, SHORT]
    E --> F[ _evaluate_direction ]
    F --> G{Conditions met?}
    G -->|Sim| H[return Signal]
    G -->|Não| I[Próxima direção]
    I --> E
    E --> J[return None + SignalEvaluation]
```

---

## 6. Regras de Negócio e Restrições

### 6.1 Invariantes

| ID | Invariante | Violação → Ação |
|---|---|---|
| INV-038-01 | LONG é avaliado antes de SHORT (prioridade histórica) | Ordem do dicionário mantida |
| INV-038-02 | SignalEvaluation sempre contém ambas as condições | Montado após o loop de direções |

---

## 7. Testes e Validação

### 7.1 Testes Obrigatórios

| ID | Descrição | Cenário |
|---|---|---|
| TEST-038-01 | Sinal LONG detectado com nova estrutura | Corpus de teste LONG |
| TEST-038-02 | Sinal SHORT detectado com nova estrutura | Corpus de teste SHORT |
| TEST-038-03 | Nenhum sinal com ambas as condições falsas | Corpus de teste NO_SIGNAL |
| TEST-038-04 | SignalEvaluation preserva condições de ambas as direções | Verificar dicionários |

### 7.2 Evidências Requeridas na PR

- [ ] Cobertura de `signal_engine.py` ≥ 95%
- [ ] Suite completa `pytest tests/strategy/` passando
- [ ] Output de `ruff check src/strategy/signal_engine.py` sem warnings

---

## 8. Tratamento de Erros

(mantido do código existente — inalterado)

---

## 9. Riscos e Mitigações

| Risco | Impacto | Mitigação |
|---|---|---|
| Bug introduzido na simetria | Alto | Testes de corpus devem detectar qualquer desvio |
| Performance degradada por lambda calls | Baixo | Avaliação é O(1) por candle — uma chamada extra é irrelevante |

---

## 10. Definição de Pronto (DoD)

- [ ] SignalEngine refatorado sem código duplicado LONG/SHORT
- [ ] `_evaluate_direction()` com parâmetros simétricos
- [ ] Todos os testes de estratégia passando
- [ ] Logging preservado (mesmos eventos, mesmos campos)
- [ ] `ruff check` limpo

---

## Histórico

- **2026-05-11:** Criação da SPEC_038.
