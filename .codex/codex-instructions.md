# Instruções do Projeto — Binance Phicube

## Idioma

**Todo conteúdo produzido neste projeto deve estar em Português do Brasil (pt-BR)**, sem exceção:

- Respostas e explicações no chat
- Comentários no código-fonte
- Docstrings de funções, classes e módulos
- Mensagens de erro e log descritivas (strings voltadas ao operador)
- Nomes de variáveis e funções devem seguir o padrão do projeto (inglês técnico é aceito para nomes de código, mas explicações sempre em pt-BR)
- Exemplos de uso e snippets gerados
- Arquivos de documentação (`.md`)
- Mensagens de commit geradas automaticamente: **inglês** (padrão Conventional Commits — exceção técnica aceita pelo time)
- Testes: descrições de `describe`, `it`, comentários e mensagens de assert em pt-BR

## Contexto do Projeto

- **Nome**: Binance Phicube
- **Tipo**: Bot de auto trade para Binance Futures USDT-M
- **Estratégia**: BO Williams Phicube (Alligator SMMA + Awesome Oscillator + Fractais de 5 barras)
- **Stack**: Python 3.11+, ccxt (async), MongoDB (motor), Docker Compose, pytest
- **Ambiente padrão**: Binance Testnet durante desenvolvimento

## Princípios de Comunicação

1. Seja direto e objetivo — o time é técnico
2. Prefira exemplos concretos a explicações genéricas
3. Ao gerar código, sempre explique *o que* e *por que*, não apenas *como*
4. Ao identificar riscos (financeiros, de segurança ou de dados), destaque explicitamente
