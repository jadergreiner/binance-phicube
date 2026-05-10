<!-- Context: core/context-system | Priority: critical | Version: 1.1 | Updated: 2026-05-10 -->

# Context System

**Purpose**: Minimal, concern-based knowledge organization for AI agents — scannable in <30s.

---

## Core Principles

### 1. Minimal Viable Information (MVI)
Core concept (1-3 sentences) → 3-5 key points → minimal example → reference link. **Files <200 lines.**

### 2. Two Structure Patterns

**Pattern A — Function-Based** (repos: `openagents-repo/`):
```
category/
├── navigation.md
├── concepts/   # What it is
├── examples/   # Working code
├── guides/     # How to
├── lookup/     # Quick reference
└── errors/     # Common issues
```

**Pattern B — Concern-Based** (dev: `development/`):
```
category/
├── navigation.md
├── {concern}/        # e.g. frontend, backend
│   └── {approach}/   # e.g. react, api-patterns
```

### 3. Token-Efficient Navigation
Each `navigation.md` has: ASCII tree + quick routes table + by-concern sections = **~200-300 tokens**.

### 4. Self-Describing Filenames
`code-quality.md` not `code.md` — no need to open files to understand content.

### 5. Knowledge Harvesting
Extract valuable context from AI summaries (`/context harvest`), then delete — workspace stays clean.

---

## Tech Placement Rules

| Scope | Path |
|---|---|
| Full-stack framework | `development/frameworks/{tech}/` |
| Specialized domain | `development/{domain}/{tech}/` |
| Layer-specific | `development/{frontend|backend}/{tech}/` |

**Core standards** (all projects) → `core/standards/`
**Dev-specific principles** → `development/principles/`

---

## Operations

| Command | Purpose |
|---|---|
| `/context` | Quick scan → suggest harvest |
| `/context harvest` | Summaries → permanent context + cleanup |
| `/context extract {source}` | From docs/code/URLs |
| `/context organize {category}` | Flat files → function folders |
| `/context update {what}` | When APIs/frameworks change |
| `/context error {error}` | Add recurring error to KB |
| `/context compact {file}` | Verbose → MVI format |
| `/context create {category}` | New category with structure |
| `/context migrate` | Global → local project-intelligence |
| `/context map` | View structure |
| `/context validate` | Check integrity, sizes, refs |

All operations show preview + require approval before writing.

---

## Success Criteria

- ✅ Minimal — <200 lines per file
- ✅ Navigable — `navigation.md` at every level
- ✅ Organized — correct pattern (function or concern)
- ✅ Token-efficient — nav files ~200-300 tokens
- ✅ Self-describing — filenames reveal content
- ✅ Referenceable — links to full docs

---

## Related

- `context-system/standards/mvi.md` — MVI deep-dive
- `context-system/standards/structure.md` — Structure patterns
- `context-system/guides/workflows.md` — Full workflow docs
- `context-system/operations/harvest.md` — Harvest operation details
