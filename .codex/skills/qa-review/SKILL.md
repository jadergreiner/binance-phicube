---
name: qa-review
description: 'Workflow de revisão de qualidade (QA) para o projeto Phicube. Use quando implementar funcionalidade nova, alterar módulos existentes, corrigir um bug, ou antes de qualquer release. Mapeia cenários de falha, verifica cobertura de testes, identifica casos de borda e propõe testes de integração com a Binance Testnet.'
argument-hint: 'Módulo ou funcionalidade a revisar (ex: order_manager.py, sinal LONG, retry logic)'
---

# Revisão de Qualidade — Phicube

Roteiro de QA para garantir que o bot de trading opere corretamente em condições normais e adversas.

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

Confirme:
- [ ] Todos os testes passando (33+ testes esperados)
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

Para cada módulo alterado, pergunte:

**API da Binance:**
- [ ] O que acontece com timeout na chamada? (ex: `fetch_ohlcv` demora > 30s)
- [ ] O que acontece com rate limit (429)? O retry com backoff está implementado?
- [ ] O que acontece se a ordem de mercado for aceita mas o SL falhar?
- [ ] O que acontece se o TP falhar após SL ser criado?

**MongoDB:**
- [ ] O que acontece se a inserção de trade falhar após a ordem já estar na Binance?
- [ ] O que acontece se `count_open_trades()` lançar exceção?
- [ ] Índice único em `entry_order_id` — o que acontece com inserção duplicada?

**Lógica do sinal:**
- [ ] O que acontece se o sinal for gerado duas vezes para o mesmo símbolo?
- [ ] O que acontece se `max_open_positions` já estiver atingido?
- [ ] O que acontece se não houver fractal válido nos últimos 100 candles?
- [ ] O que acontece com DataFrame com menos de 50 linhas?

### 4. Verificar casos de borda nos indicadores

- [ ] SMMA com série muito curta (menos de `period` valores)
- [ ] AO com valores de high/low iguais (spread zero)
- [ ] Fractal com high/low empatados com vizinhos (não deve ser detectado)
- [ ] DataFrame sem nenhum fractal válido no lookback

### 5. Propor testes ausentes

Para cada cenário identificado no passo 3 sem cobertura, descreva o teste a implementar:

```python
# Exemplo de estrutura
@pytest.mark.asyncio
async def test_order_manager_sl_failure_cancels_all_orders():
    """Se o SL falhar após abertura da posição, cancel_all_orders deve ser chamado."""
    ...
```

Priorize por impacto financeiro: falhas que podem resultar em posição aberta sem proteção são **P0**.

### 6. Validar integração com Binance Testnet (se disponível)

Se o ambiente de Testnet estiver configurado (`.env` com credenciais de testnet):

```bash
# Executar testes de integração marcados
pytest -v -m integration
```

Confirme:
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
