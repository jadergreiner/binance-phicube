# Conhecimentos Específicos — Backend Sênior

## Python e Programação Assíncrona

- Python 3.11+: tipagem estática, dataclasses, Pydantic v2
- asyncio: event loop, tasks, gather, cancelamento seguro
- Tratamento robusto de exceções em contextos assíncronos
- Padrões de retry com backoff exponencial

## Integração com Binance

- API REST Binance Futures (USDT-M): autenticação HMAC, rate limits, paginação
- WebSocket Binance: streams de user data, klines, book ticker
- Biblioteca ccxt (async): criação de ordens, consulta de saldo, posições abertas
- Tipos de ordens Futures: MARKET, LIMIT, STOP_MARKET, TAKE_PROFIT_MARKET, reduceOnly
- Gestão de API Keys: armazenamento seguro, rotação, permissões mínimas necessárias

## Arquitetura e Persistência

- Design de sistemas event-driven e loops de polling assíncronos
- MongoDB com motor (async): modelagem de documentos, índices, upserts
- Logging estruturado (structlog / JSON) para rastreabilidade e auditoria
- Pydantic Settings para configuração via variáveis de ambiente

## Confiabilidade

- Circuit breakers e graceful shutdown em sistemas Python
- Healthchecks e recuperação automática de conexões perdidas
- Estratégias de idempotência em execução de ordens (evitar ordens duplicadas)
