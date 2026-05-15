## Context

O projeto tem múltiplas dataclasses com serialização manual para dicionário, repetindo padrão de `to_dict()` em diferentes módulos. Isso gera risco de omissão de campos após evolução de modelo e eleva custo de manutenção transversal.

A mudança é cross-cutting: estratégia, risco, ordem e backtest compartilham o mesmo problema de serialização.

## Goals / Non-Goals

**Goals:**
- Padronizar contrato de serialização em um protocolo único.
- Reduzir boilerplate de `to_dict()` manual em dataclasses elegíveis.
- Garantir compatibilidade de payload com os formatos já consumidos por armazenamento/logs/API.
- Definir comportamento para campos aninhados e coleções.

**Non-Goals:**
- Introduzir serialização binária ou formatos alternativos (protobuf/avro/msgpack).
- Versionar schemas de payload nesta mudança.
- Alterar semântica de domínio dos modelos (apenas serialização).

## Decisions

### 1) Introduzir protocolo `Serializable` no módulo comum
**Decisão:** criar protocolo com `to_dict()` como contrato de fronteira para componentes genéricos.

**Racional:** melhora legibilidade do contrato e permite validação estática de consumidores que dependem de serialização.

**Alternativas consideradas:**
- manter duck typing implícito sem protocolo: menor formalismo, maior ambiguidade de contrato.

### 2) Usar decorator `@auto_dict` para dataclasses
**Decisão:** fornecer decorator para gerar `to_dict()` automaticamente em dataclasses, preservando método manual quando já existir e for explicitamente necessário.

**Racional:** elimina repetição sem forçar herança, mantendo flexibilidade de override pontual.

**Pattern aplicado:** `Decorator` (composição de comportamento de serialização sem alterar hierarquia de classes).

**Alternativas consideradas:**
- classe base abstrata com herança obrigatória: aumenta acoplamento estrutural.
- metaclass: custo cognitivo maior sem benefício proporcional.

### 3) Suporte recursivo controlado para estruturas comuns
**Decisão:** serialização automática tratar:
- campos primitivos diretamente;
- objetos com `to_dict()` de forma recursiva;
- listas de objetos serializáveis.

**Racional:** cobre os casos predominantes do projeto sem impor framework externo.

**Pattern aplicado:** `Adapter` para tipos não serializáveis diretamente (ex.: estruturas externas) através de adaptadores explícitos por tipo.

### 4) Segurança por política explícita
**Decisão:** definir regra de não serialização de segredos (`api_key`, `api_secret`, tokens e equivalentes sensíveis), via política de exclusão/mascaração.

**Racional:** evita vazamento acidental em logs ou persistência.

**Pattern aplicado:** `Strategy` para política de proteção de campos sensíveis (ex.: `omit`, `mask`, `custom`), selecionável sem alterar o núcleo de serialização.

## Risks / Trade-offs

- [Mudança de payload em campos opcionais] -> Mitigar com testes de snapshot/paridade para modelos críticos.
- [Refatoração ampla com regressão silenciosa] -> Migrar em lotes pequenos e validar por módulo.
- [Decorator aplicado fora de dataclass] -> Falhar cedo com `TypeError` claro no import.
- [Overhead de reflexão] -> Limitar reflexão ao tempo de definição da classe, não ao hot path de execução.

## Migration Plan

1. Criar módulo comum com `Serializable` e `@auto_dict`.
2. Cobrir comportamento com testes unitários dedicados.
3. Migrar modelos prioritários (Signal, PositionSize, Trade, SignalEvaluation).
4. Validar paridade de payloads e ajustar casos especiais que exigem `to_dict` manual.
5. Avaliar extensão para modelos de backtest em etapa final da mudança.

Rollback:
- reverter apenas dataclasses migradas e manter módulo comum sem uso até nova iteração.

## Open Questions

- Quais campos sensíveis devem ser explicitamente mascarados vs omitidos?
- `BacktestTrade` e `BacktestResult` entram nesta mesma change ou em subetapa opcional?
