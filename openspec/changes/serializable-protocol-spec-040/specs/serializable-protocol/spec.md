## ADDED Requirements

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
