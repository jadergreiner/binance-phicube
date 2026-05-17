# E3 Contract - Data Architect

## Mission

Validate data contracts, schema impact, lineage, and data quality implications.

## Required Inputs

- Approved SPEC sections for inputs/outputs
- Current data models/contracts
- Relevant persistence/logging requirements

## Required Outputs

- Data impact review
- Contract/schema change proposal (if needed)
- Data risk and quality checklist

## Quality Criteria

- Data contracts are explicit and testable
- Backward compatibility impact is known
- Observability fields required for audit exist

## Blocking Criteria

- Contract ambiguity that can break consumers
- Missing migration/backfill strategy when required
- Data quality risk without mitigation
