<!-- Context: standards/intelligence-mgmt | Priority: high | Version: 1.1 | Updated: 2026-05-10 -->

# Project Intelligence Management

> How to manage project intelligence files. See `project-intelligence.md` for what and why.

---

## Quick Reference

| Action | Do This |
|--------|---------|
| Update file | Edit + bump frontmatter version |
| Add file | Create `.md` + add to `navigation.md` |
| Add subfolder | Folder + `navigation.md` + update parent nav |
| Deprecate file | Rename `.deprecated.md` (never delete) |

---

## Update Existing Files

**When**: Business changes, new decisions, new issues, feature launch, stack changes.

**Process**:
1. Edit file, update frontmatter: `<!-- Context: {cat} | Priority: {level} | Version: {X.Y} | Updated: {YYYY-MM-DD} -->`
2. Keep <200 lines
3. Commit: `docs: Update {file} with {what changed}`

## Add New Files

**Naming**: kebab-case, descriptive (e.g., `user-research.md`).

**Requirements**:
- Frontmatter with all fields
- Quick Reference section
- <200 lines
- Added to `navigation.md`
- Linked from related files

**Subfolders**: Only when 5+ related files exist. Every subfolder **must** have `navigation.md`. Max 2 levels deep.

## Deprecate Files (Never Delete)

1. Rename: `file.md` → `file.deprecated.md`
2. Frontmatter: `<!-- DEPRECATED: {date} - {reason} -->` + `<!-- REPLACED BY: {new-file} -->`
3. Banner: `⚠️ DEPRECATED: See {new-file} for current info`
4. Mark deprecated in `navigation.md`

## Version Tracking

| Change | Version |
|--------|---------|
| New file | 1.0 |
| Content update | MINOR |
| Structure change | MAJOR |
| Typo fix | PATCH |

Frontmatter date always `YYYY-MM-DD`.

## Quality Standards

- Files: <200 lines
- Sections: 3–7 per file
- Required: Frontmatter, Quick Reference, Related files
- Anti-patterns: mix concerns, exceed 200L, delete files, skip frontmatter, duplicate info

## Governance

| Area | Owner |
|------|-------|
| Business domain | Product Owner |
| Technical domain | Tech Lead |
| Decisions log | Tech Lead |
| Living notes | Team |

**Review**: Quick per PR / Full quarterly / Archive semi-annually.

## Related

- `project-intelligence.md` — Standard
- `../../project-intelligence/navigation.md` — Project intelligence nav
- `../context-system.md` — Context system overview
