# Conhecimentos Específicos — QA Engineer

## Testes Automatizados em Python

- pytest: fixtures, parametrize, conftest.py, marcadores customizados
- pytest-asyncio: testes de código assíncrono (asyncio), event loop compartilhado
- pytest-mock: mock de dependências externas (ccxt, motor, structlog)
- Cobertura de código: pytest-cov, relatórios de cobertura por módulo
- Testes de propriedade (property-based testing): Hypothesis para estratégias e cálculos numéricos

## Testes de Integração

- Testes contra a Binance Testnet (USDT-M Futures Sandbox) com dados reais da API
- Testes de integração com MongoDB real em container (testcontainers-python ou docker-compose de teste)
- Validação do fluxo completo: sinal → cálculo de posição → execução → persistência → consulta

## Cenários de Falha e Resiliência

- Simulação de falhas de API: timeout, rate limit (429), erro de servidor (502/503), resposta malformada
- Simulação de falha do MongoDB durante operação em andamento
- Teste de idempotência: o que acontece se o mesmo sinal for processado duas vezes?
- Teste de condição de corrida: dois sinais simultâneos para o mesmo símbolo

## Testes de Carga e Performance

- Locust ou k6 para simular múltiplos pares sendo monitorados simultaneamente
- Medição de latência entre detecção de sinal e execução da ordem
- Validação de comportamento sob condições de alta volatilidade (muitos candles chegando ao mesmo tempo)

## Ambientes de Teste

- Gerenciamento de dados de teste: fixtures de OHLCV realistas para diferentes cenários de mercado
- Ambiente de staging com Docker Compose idêntico à produção
