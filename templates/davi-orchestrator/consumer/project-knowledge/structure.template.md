# Consumer Project Knowledge Structure

Use this structure in each repository that consumes Davi:

```text
.davi/
  project-knowledge/
    business/
      README.md
    architecture/
      README.md
    governance/
      README.md
```

## Rules

- Store only project-specific knowledge in this structure.
- Keep Davi core rules/policies in `agent-davi`.
- Link local artifacts to cycle IDs and approval evidence.
