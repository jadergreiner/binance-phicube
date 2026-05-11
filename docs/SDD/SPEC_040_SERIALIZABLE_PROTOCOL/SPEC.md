# SPEC_040 — Protocolo `Serializable` + Padronização `to_dict`

**ID:** SPEC_040
**Status:** Rascunho
**Data:** 2026-05-11
**Versão:** 1.0
**Dependências:** SPEC_039 (common/ pattern)
**Skill de validação:** `sdd-spec-driven-development`, `qa-review`

---

## 1. Título e Resumo

### 1.1 Nome da Funcionalidade

Protocolo `Serializable` para serialização padronizada de dataclasses

### 1.2 Resumo

**O que é:** Definição de um protocolo `Serializable` com método `to_dict()` e registro de dataclasses como serializáveis via decorador ou herança, eliminando a implementação manual de `to_dict()` em 6+ dataclasses.

**Por que estamos fazendo:** Cada dataclass (Signal, PositionSize, Trade, SignalEvaluation, BacktestTrade, BacktestResult, etc.) implementa `to_dict()` manualmente com o mesmo padrão: `return {"field": self.field, ...}`. Isso é boilerplate repetitivo, propenso a erros de omissão quando novos campos são adicionados, e sem verificação estática de tipo.

**Valor de negócio:** Reduz ~100 linhas de boilerplate, garante que `to_dict()` reflita sempre todos os campos, elimina bugs de omissão em serializações parciais.

**Conexão com PRD/SPEC:** Transversal — aplica-se a todos os dataclasses que cruzam fronteira módulo → MongoDB / API / log.

---

## 2. Objetivos e Escopo

### 2.1 Objetivos

- [ ] Definir `common/serialization.py` com protocolo `Serializable`
- [ ] Implementar `@auto_dict` decorator que gera `to_dict()` automaticamente para dataclasses
- [ ] Refatorar dataclasses existentes para usar o decorador
- [ ] Opcional: `to_json()` e `from_dict()` se houver demanda

### 2.2 Fora do Escopo

- **Não inclui:** Serialização binária (protobuf, avro, msgpack)
- **Não inclui:** Schema registry ou versionamento de schema
- **Não inclui:** Mudança no formato dos dicionários gerados (compatibilidade garantida)

---

## 3. Referências

| Documento | Seção | Relevância |
|---|---|---|
| `src/strategy/signal_engine.py` | `Signal.to_dict()` | Alvo da refatoração |
| `src/trading/risk_manager.py` | `PositionSize.to_dict()` | Alvo da refatoração |
| `src/trading/order_manager.py` | `Trade.to_dict()` | Alvo da refatoração |
| `src/backtest/models.py` | `BacktestTrade` (sem to_dict) | Potencial alvo |
| `docs/CODEX_BEST_PRACTICES_ADOPTION.md` | — | Padrões de código |

---

## 4. Histórias de Usuário e Requisitos

### US-040-01: Protocolo `Serializable`

> Como **desenvolvedor**, quero **um protocolo `Serializable` com método `to_dict()`** para **poder escrever código genérico que serialize qualquer objeto sem conhecer seu tipo concreto**.

```python
class Serializable(Protocol):
    def to_dict(self) -> dict: ...
```

- [ ] AC-01: `isinstance(obj, Serializable)` funciona para objetos com `to_dict`
- [ ] AC-02: Funções que aceitam `Serializable` aceitam qualquer dataclass refatorada

### US-040-02: Decorador `@auto_dict`

> Como **desenvolvedor**, quero **um decorador `@auto_dict` que gera `to_dict()` automaticamente para qualquer dataclass** para **eliminar a implementação manual**.

```python
@auto_dict
@dataclass(frozen=True)
class PositionSize:
    symbol: str
    quantity: float

# Gera automaticamente:
# def to_dict(self) -> dict:
#     return {
#         "symbol": self.symbol,
#         "quantity": self.quantity,
#         ...
#     }
```

- [ ] AC-01: `@auto_dict` gera `to_dict()` com todos os campos da dataclass
- [ ] AC-02: Campos sem anotação de tipo são incluídos
- [ ] AC-03: Funciona com `@dataclass(frozen=True)` e `@dataclass`
- [ ] AC-04: Suporta `field(default_factory=...)` preservando omitição de defaults

---

## 5. Design e Arquitetura

### 5.1 Módulo `common/serialization.py`

```python
from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import Protocol, TypeVar

T = TypeVar("T", bound="Serializable")


class Serializable(Protocol):
    """Protocolo para objetos que podem ser serializados para dict."""
    def to_dict(self) -> dict:
        ...


def auto_dict(cls: type[T]) -> type[T]:
    """Decorador que injeta to_dict() em uma dataclass.

    Gera automaticamente um método to_dict() que serializa
    todos os campos da dataclass, incluindo campos com
    default_factory.

    Uso:
        @auto_dict
        @dataclass
        class MeuModelo:
            nome: str
            valor: float
    """
    if not is_dataclass(cls):
        raise TypeError(f"@auto_dict requires a dataclass, got {cls.__name__}")

    existing = getattr(cls, "to_dict", None)
    if existing is not None:
        return cls  # já tem to_dict manual — não sobrescrever

    field_list = fields(cls)

    def to_dict(self) -> dict:
        result: dict = {}
        for f in field_list:
            value = getattr(self, f.name)
            if hasattr(value, "to_dict") and callable(value.to_dict):
                result[f.name] = value.to_dict()
            elif isinstance(value, list):
                result[f.name] = [
                    item.to_dict() if hasattr(item, "to_dict") and callable(item.to_dict)
                    else item
                    for item in value
                ]
            else:
                result[f.name] = value
        return result

    cls.to_dict = to_dict  # type: ignore[method-assign]
    return cls
```

### 5.2 Dataclasses Afetadas

| Dataclass | Arquivo | Linhas de to_dict | Ação |
|---|---|---|---|
| `Signal` | `src/strategy/signal_engine.py` | 13 linhas | Adicionar `@auto_dict`, remover manual |
| `PositionSize` | `src/trading/risk_manager.py` | 12 linhas | Adicionar `@auto_dict`, remover manual |
| `Trade` | `src/trading/order_manager.py` | 23 linhas | Adicionar `@auto_dict`, remover manual |
| `SignalEvaluation` | `src/strategy/signal_engine.py` | 13 linhas | Adicionar `@auto_dict`, remover manual |
| `BacktestTrade` | `src/backtest/models.py` | (sem to_dict) | Adicionar `@auto_dict` + adicionar se necessário |
| `BacktestResult` | `src/backtest/models.py` | (sem to_dict) | Adicionar `@auto_dict` se necessário |

### 5.3 Tratamento de Campos Complexos

Para campos que são outras dataclasses serializáveis, `@auto_dict` recursivamente chama `to_dict()`. Para listas de objetos serializáveis, itera e chama `to_dict()` em cada item. Para tipos primitivos, usa o valor diretamente.

---

## 6. Regras de Negócio e Restrições

### 6.1 Invariantes

| ID | Invariante | Violação → Ação |
|---|---|---|
| INV-040-01 | `to_dict()` nunca levanta exceção | Erro de serialização → log + retorna dict parcial |
| INV-040-02 | `to_dict()` inclui TODOS os campos da dataclass | Verificação via teste comparando fields() vs keys() |

### 6.2 Padrões de Segurança

- `to_dict()` nunca serializa `api_key`, `api_secret` ou tokens
- Campos com anotação `SecretStr` do Pydantic são omitidos ou mascarados

---

## 7. Testes e Validação

### 7.1 Testes Unitários

| ID | Descrição | Cenário |
|---|---|---|
| TEST-040-01 | @auto_dict gera to_dict com todos os campos | Dataclass de 5 campos |
| TEST-040-02 | @auto_dict não sobrescreve to_dict manual | Dataclass com to_dict existente |
| TEST-040-03 | Serialização recursiva de sub-dataclasses | Dataclass com campo Serializable |
| TEST-040-04 | Serialização de listas de objetos | Lista de PositionSize |
| TEST-040-05 | TypeError se aplicado a não-dataclass | Classe comum → TypeError |

### 7.2 Evidências Requeridas na PR

- [ ] `pytest tests/common/test_serialization.py` passando
- [ ] `to_dict()` de cada dataclass refatorada produz output idêntico ao anterior

---

## 8. Tratamento de Erros

| Erro / Condição | Causa | Ação do Sistema |
|---|---|---|
| `TypeError` | `@auto_dict` aplicado a não-dataclass | Erro em tempo de importação — detectado em dev |
| Campo com valor não serializável | Tipo não suportado (exceção em getattr) | Log + retorna string repr |

---

## 9. Riscos e Mitigações

| Risco | Impacto | Mitigação |
|---|---|---|
| Mudança na ordem dos campos do dict | Baixo | Python 3.7+ mantém ordem de inserção (igual à declaração) |
| Performance de `@auto_dict` | Muito baixo | Reflexão acontece uma vez, no import |

---

## 10. Definição de Pronto (DoD)

- [ ] `common/serialization.py` com `Serializable` e `@auto_dict`
- [ ] Pelo menos 4 dataclasses refatoradas: Signal, PositionSize, SignalEvaluation, Trade
- [ ] Output de `to_dict()` idêntico ao anterior (verificado por snapshot tests)
- [ ] Testes unitários para o módulo

---

## Histórico

- **2026-05-11:** Criação da SPEC_040.
