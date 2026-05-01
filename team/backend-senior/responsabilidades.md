# Responsabilidades — Backend Sênior

## Arquitetura do Sistema

- Projetar e manter a arquitetura geral do sistema: módulos, dependências e contratos de interface
- Garantir que o design suporte extensibilidade (novos símbolos, timeframes, estratégias futuras) sem reescritas
- Decisão técnica sobre padrões de código, estrutura de pastas e convenções do projeto

## Integração com a Binance

- Implementar e manter o cliente Binance Futures (`BinanceClient`): autenticação, rate limiting, retry
- Garantir execução segura de ordens: entrada de mercado, stop loss e take profit como ordens protegidas
- Implementar mecanismo de cancelamento automático em caso de falha parcial (nunca deixar posição sem SL)
- Monitorar mudanças na API da Binance que possam quebrar a integração

## Confiabilidade e Observabilidade

- Implementar logging estruturado em todos os módulos críticos
- Garantir graceful shutdown: o sistema encerra sem deixar ordens ou posições abertas sem proteção
- Implementar healthchecks e mecanismos de reconexão automática

## Colaboração Técnica

- Realizar code review de todos os PRs da equipe técnica
- Apoiar o Quant Developer na integração do motor de sinais com o loop principal
- Apoiar o DevOps na configuração do ambiente de produção Docker
- Ser o ponto de escalação técnica quando outros engenheiros encontrarem bloqueios
