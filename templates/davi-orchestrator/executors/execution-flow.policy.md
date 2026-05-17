# Executors Execution Flow Policy

## Default Sequence

1. E1 receives approved Tasks and opens execution lane.
2. E2 reviews technical solution and constraints.
3. E3 reviews data impact when data contracts are affected.
4. E4 reviews ML impact when ML/runtime is affected.
5. E5 implements approved tasks.
6. E6 validates acceptance and regression evidence.
7. E1 consolidates closure package.

## Parallelization Rules

- E2 and E3 can run in parallel when scopes are independent.
- E4 can run in parallel with E3 when ML and data scopes are independent.
- E5 starts only after required upstream reviews are completed.

## Mandatory Gates

- Gate G1: SPEC + Tasks approved.
- Gate G2: Required architecture/data/ML reviews complete.
- Gate G3: Implementation evidence complete and lint gate `PASS`.
- Gate G4: QA acceptance decision recorded.

## Return-to-Refiner Rule

If any executor identifies scope ambiguity or conflict with approved SPEC/Tasks,
execution is blocked and returned to Refiner stage for clarification.
