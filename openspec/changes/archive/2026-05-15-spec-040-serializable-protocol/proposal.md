## Why

Atualmente, múltiplas dataclasses do projeto implementam `to_dict()`
manualmente com padrões repetitivos, o que aumenta boilerplate e risco de
omissão de campos quando o modelo evolui. Esta mudança é necessária agora para
padronizar serialização entre bot, API e persistência Mongo, reduzindo risco
operacional e custo de manutenção.

## What Changes

- Introduzir um protocolo `Serializable` para formalizar o contrato de serialização (`to_dict()`).
- Introduzir um mecanismo padronizado de geração de `to_dict()` para dataclasses (via decorador), com suporte a campos simples, objetos serializáveis aninhados e listas.
- Refatorar dataclasses prioritárias para adoção do novo padrão, removendo implementações manuais duplicadas.
- Definir requisitos de compatibilidade para manter o formato atual dos dicionários serializados e evitar regressões em Mongo/API/logs.
- Definir requisitos de segurança para evitar serialização indevida de segredos.

## Capabilities

### New Capabilities

- `serializable-protocol`: Contrato e padronização de serialização de dataclasses para `dict`, com geração automática e regras de compatibilidade/segurança.

### Modified Capabilities

- Nenhuma.

## Impact

- Código afetado: `src/common/` (novo módulo de serialização), dataclasses em `src/strategy/`, `src/trading/` e possivelmente `src/backtest/`.
- Persistência/API: impacto indireto em payloads serializados para MongoDB e respostas/objetos consumidos por camadas internas.
- Testes: novos testes unitários para o protocolo/decorador e atualização de testes de regressão de `to_dict()`.
- Dependências: sem novas dependências externas obrigatórias; mudança concentrada em padronização interna.
