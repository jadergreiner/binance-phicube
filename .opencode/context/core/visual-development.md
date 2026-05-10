<!-- Context: visual-development | Priority: high | Version: 1.1 | Updated: 2026-05-10 -->
# Visual Development Context

**Purpose**: Visual content creation, UI design, image generation, and diagram creation via Image Specialist subagent.

---

## Quick Routes

| Task | Context | Subagent |
|------|---------|----------|
| Generate image/diagram | This file | Image Specialist |
| Edit existing image | This file | Image Specialist |
| UI mockup (static) | This file | Image Specialist |
| Interactive UI design | `workflows/design-iteration-overview.md` | — |
| Design system | `ui/web/design-systems.md` | — |
| UI standards | `ui/web/ui-styling-standards.md` | — |

---

## Image Specialist

**When to delegate**: User asks for image, diagram, mockup, graphic, icon, illustration, screenshot.

**Invocation pattern**:
```javascript
task(
  subagent_type="Image Specialist",
  description="Brief 3-5 word description",
  prompt="Load: .opencode/context/core/visual-development.md

Task: [detailed visual requirement]

Requirements:
- Style: [aesthetic — modern, minimalist, professional]
- Dimensions: [WxH or aspect ratio]
- Key Elements: [must-include items]
- Colors: [scheme / hex codes]
- Format: [PNG, JPG, SVG]
Output: [path to save file]"
)
```

---

## Decision Tree: Image Specialist vs Design Iteration

```
User needs visual content
  ↓
Interactive/responsive HTML/CSS?
  ↓
YES → design-iteration-overview.md (HTML/CSS code)
NO  → Is it a static visual asset?
        ↓
      YES → Image Specialist (diagrams, mockups, graphics)
      NO  → Clarify with user
```

| Need | Use |
|------|-----|
| Interactive dashboard | design-iteration-overview.md |
| Dashboard mockup (static) | Image Specialist |
| Architecture diagram | Image Specialist |
| Social media graphic | Image Specialist |

---

## Best Practices

✅ **Do**: Specify dimensions + format + style + colors + key elements + output path
❌ **Don't**: Vague descriptions, skip dimensions, assume defaults, omit output location

---

## Related

- `workflows/design-iteration-overview.md` — Interactive UI workflow
- `ui/web/design-systems.md` — Design systems
- `ui/web/ui-styling-standards.md` — UI standards
- `openagents-repo/guides/subagent-invocation.md` — Subagent invocation guide
