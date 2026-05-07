---
name: qa-review
description: Workflow replicado de .claude/commands/qa-review.md para 'Revisão de Qualidade — Phicube'. Use quando precisar executar esse procedimento no projeto Binance Phicube.
---

# Revisão de Qualidade — Phicube

Roteiro de QA para garantir que o bot de trading opere corretamente em condições normais e adversas.

**Argumento:** módulo ou funcionalidade a revisar (ex: `order_manager.py`, `sinal LONG`, `retry logic`)

## Quando Usar

- Após implementar funcionalidade nova
- Ao corrigir um bug crítico
- Antes de qualquer release para produção
- Ao alterar módulos de strategy, trading ou storage

## Procedimento

### 1. Executar a suite de testes existente

```bash
pytest -v
```

- [ ] Todos os testes passando
- [ ] Nenhum warning de `asyncio` ou `deprecation` novo
- [ ] Tempo de execução dentro do esperado (< 30s para testes unitários)

### 2. Verificar cobertura por módulo

```bash
pytest --cov=src --cov-report=term-missing
```

Meta mínima por módulo crítico:

| Módulo | Cobertura mínima |
|--------|-----------------|
| `strategy/indicators.py` | 90% |
| `strategy/signal_engine.py` | 85% |
| `trading/risk_manager.py` | 80% |
| `trading/order_manager.py` | 75% |
| `storage/repository.py` | 75% |

### 3. Mapear cenários de falha não cobertos

**API da Binance:**
- [ ] Timeout na chamada? (ex: `fetch_ohlcv` demora > 30s)
- [ ] Rate limit (429)? O retry com backoff está implementado?
- [ ] Ordem de mercado aceita mas o SL falha?
- [ ] TP falha após SL ser criado?

**MongoDB:**
- [ ] Inserção de trade falha após a ordem já estar na Binance?
- [ ] `count_open_trades()` lança exceção?
- [ ] Índice único em `entry_order_id` — comportamento com inserção duplicada?

**Lógica do sinal:**
- [ ] Sinal gerado duas vezes para o mesmo símbolo?
- [ ] `max_open_positions` já atingido?
- [ ] Sem fractal válido nos últimos 100 candles?
- [ ] DataFrame com menos de 50 linhas?

### 4. Verificar casos de borda nos indicadores

- [ ] SMMA com série muito curta (menos de `period` valores)
- [ ] AO com valores de high/low iguais (spread zero)
- [ ] Fractal com high/low empatados com vizinhos (não deve ser detectado)
- [ ] DataFrame sem nenhum fractal válido no lookback

### 5. Propor testes ausentes

Para cada cenário sem cobertura, descreva o teste a implementar. Priorize por impacto financeiro: falhas que resultam em posição aberta sem proteção são **P0**.

```python
@pytest.mark.asyncio
async def test_order_manager_sl_failure_cancels_all_orders():
    """Se o SL falhar após abertura da posição, cancel_all_orders deve ser chamado."""
    ...
```

### 6. Validar integração com Binance Testnet (se disponível)

```bash
pytest -v -m integration
```

- [ ] Conexão com Testnet bem-sucedida
- [ ] Saldo em USDT disponível no Testnet
- [ ] Criação de ordem de mercado retorna ID válido
- [ ] Cancelamento de ordens funciona

## Critérios de Conclusão

- [ ] Suite completa passando sem regressão
- [ ] Cobertura mínima atingida nos módulos críticos
- [ ] Todos os cenários P0 (posição sem proteção) cobertos por teste
- [ ] Novos testes propostos documentados ou implementados
- [ ] Resultado reportado ao Backend Sênior antes do merge

