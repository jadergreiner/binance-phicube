# serializable-protocol Specification

## Purpose
TBD - created by archiving change spec-040-serializable-protocol. Update Purpose after archive.
## Requirements
### Requirement: Contrato de serialização padronizado

O sistema SHALL definir um contrato explícito de serialização para objetos de
domínio, baseado em método `to_dict()` e aplicável em código tipado para
persistência, API e fluxos internos.

#### Scenario: Aceitação de objetos serializáveis por contrato

- **WHEN** uma função tipada para o contrato de serialização receber um objeto
  que implementa `to_dict()`
- **THEN** a função MUST aceitar o objeto sem depender do tipo concreto

### Requirement: Geração automática de to_dict para dataclasses

O sistema SHALL oferecer um mecanismo reutilizável para gerar `to_dict()`
automaticamente em dataclasses elegíveis, evitando duplicação de implementação
manual.

#### Scenario: Geração de serialização para todos os campos declarados

- **WHEN** uma dataclass elegível for marcada para serialização automática
- **THEN** o `to_dict()` gerado MUST incluir todas as chaves correspondentes aos
  campos declarados na dataclass

#### Scenario: Preservação de implementação manual existente

- **WHEN** uma dataclass já possuir `to_dict()` implementado manualmente
- **THEN** o mecanismo automático MUST preservar essa implementação sem
  sobrescrever seu comportamento

### Requirement: Serialização de estruturas aninhadas

O sistema SHALL suportar serialização consistente de campos com objetos
serializáveis aninhados e coleções desses objetos.

#### Scenario: Campo aninhado serializável

- **WHEN** uma dataclass contiver campo cujo valor implemente `to_dict()`
- **THEN** o resultado serializado MUST incluir esse campo convertido por
  `to_dict()` recursivamente

#### Scenario: Lista de objetos serializáveis

- **WHEN** uma dataclass contiver lista com itens que implementam `to_dict()`
- **THEN** o resultado serializado MUST converter cada item da lista usando
  `to_dict()` mantendo a ordem original

### Requirement: Compatibilidade do formato serializado

O sistema MUST manter compatibilidade do formato serializado para dataclasses
refatoradas, preservando nomes de campos e semântica dos valores esperados
pelos consumidores atuais.

#### Scenario: Paridade de payload após refatoração

- **WHEN** uma dataclass com `to_dict()` manual for migrada para serialização
  automática
- **THEN** o dicionário resultante MUST permanecer compatível com o formato
  anteriormente produzido para os mesmos dados de entrada

### Requirement: Proteção contra vazamento de segredos

O sistema MUST impedir serialização indevida de informações sensíveis no fluxo
padronizado de `to_dict()`.

#### Scenario: Campo sensível identificado

- **WHEN** um objeto serializável contiver campo classificado como segredo
- **THEN** o resultado serializado MUST omitir ou mascarar esse campo conforme
  política de segurança definida pelo projeto

### Requirement: Serializable Contract
The system SHALL provide a common serialization contract via a `Serializable` protocol with a `to_dict()` method for model-level interoperability.

#### Scenario: Generic serializer consumer
- **WHEN** a component accepts objects typed as `Serializable`
- **THEN** it MUST be able to call `to_dict()` without requiring concrete model knowledge

### Requirement: Automatic Dataclass Dictionary Serialization
The system SHALL provide an `@auto_dict` mechanism that generates `to_dict()` for eligible dataclasses using all declared fields.

#### Scenario: Decorated dataclass serialization
- **WHEN** a dataclass is decorated with `@auto_dict`
- **THEN** the generated `to_dict()` MUST include all declared dataclass fields

#### Scenario: Existing manual serializer preservation
- **WHEN** a dataclass already provides an explicit `to_dict()`
- **THEN** automatic generation MUST NOT overwrite the existing manual behavior

#### Scenario: Decorator behavior without inheritance coupling
- **WHEN** a model is migrated to `@auto_dict`
- **THEN** the model MUST gain serialization behavior without requiring inheritance from a serialization base class

### Requirement: Nested and Collection Serialization
The system SHALL support recursive serialization for common nested structures.

#### Scenario: Nested serializable field
- **WHEN** a dataclass field contains an object exposing `to_dict()`
- **THEN** serialization MUST include the nested object as a dictionary

#### Scenario: List of serializable items
- **WHEN** a dataclass field contains a list of serializable objects
- **THEN** serialization MUST output a list of dictionaries in the same order

#### Scenario: Adapter path for non-serializable external types
- **WHEN** a field contains a type that is not natively serializable by the core rules
- **THEN** the system MUST allow explicit adaptation before serialization output

#### Scenario: Datetime compatibility for existing consumers
- **WHEN** a migrated model contains `datetime` fields already consumed by repository/API
- **THEN** serialized output MUST preserve the pre-migration value format expected by those consumers

#### Scenario: Cyclic reference protection
- **WHEN** nested objects form a cyclic reference chain
- **THEN** serialization MUST fail deterministically with explicit error handling instead of unbounded recursion

### Requirement: Sensitive Data Protection in Serialization
The system SHALL prevent accidental exposure of secret values in auto-generated serialization output.

#### Scenario: Secret-like field names
- **WHEN** a model contains sensitive fields (e.g., `api_key`, `api_secret`, token-like secrets)
- **THEN** serialization MUST apply the configured protection policy (omit or mask) instead of raw disclosure

#### Scenario: Strategy-swappable protection policy
- **WHEN** the protection policy changes between `omit` and `mask`
- **THEN** serialized output MUST reflect the selected policy without changing model code

### Requirement: Backward-Compatible Payload Shape for Migrated Models
The system SHALL preserve payload compatibility for migrated dataclasses that are consumed by storage, API, or logging paths.

#### Scenario: Migration parity for core models
- **WHEN** a model is migrated from manual `to_dict()` to `@auto_dict`
- **THEN** the serialized output MUST remain behaviorally compatible with prior expected keys and value types

#### Scenario: Field inclusion parity for optional values
- **WHEN** migrated models contain optional fields with `None` values
- **THEN** key presence and value representation MUST remain compatible with prior manual serializer behavior

