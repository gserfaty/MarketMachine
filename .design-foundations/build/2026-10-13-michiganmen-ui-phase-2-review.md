# Design Review: Phase 2 - michiganmen "Open House" DESIGN.md

## Rendered Evidence
- Screenshot: none (spec-only phase; structure/token-level critique, pixel checks unverified, noted gap)
- Surface: /Users/gabriel/code/michiganmen/DESIGN.md
## Assessment B
- Exit: 3 N/A (no rendered artifact). Not a skipped detector.
## Triage
- Baseline: visual + usability. Dispatched: color, fonts, design-dna (token spec). N/A: data-viz, content-design, journey, behavioral.

## Findings
| Severity | Pillar | Problem | Principle | Fix |
|---|---|---|---|---|
| Minor | color | --error-text (#974843) is visually near-identical to --accent-text/--accent-solid-hover (#974847); separation relies wholly on form (container, left border, X icon, "Error:" wording) | Redundant coding (ch08); Nielsen #1/#9 | Acceptable per edge-case rule; optionally shift error hue (e.g. toward orange) |
| Minor | color | --text-secondary on --surface-active (neutral-4) not reported | WCAG 1.4.3 | Add pair to report if used |
| Note | distinctiveness | Direction nameable: "Roofline + serif answer sentence on airy white"; Roofline is non-generic | ai-tells CHECKER | none |

## Requirement Fulfillment
### DW-2.1
PREMISE: DESIGN.md locked (token block present + user-confirmed).
EVIDENCE: Status line "LOCKED - user-confirmed 2026-10-13 (chose Open House)"; full :root token block present. (Open questions section still lists "Lock: user picks..." - stale text, non-blocking.)
VERDICT: PASS
### DW-2.2
PREMISE: All text/background pairs pass WCAG AA, verified via palette.mjs.
EVIDENCE: Re-ran palette.mjs --seed 22 --chroma balanced --harmony triadic --scheme light: exit 0, all reported pairs PASS, values match DESIGN.md. Independently computed overrides: text/bg 13.30, text-secondary/bg 5.89, /surface 5.70, /hover 5.29; white on accent-solid 4.88, on hover 6.30; accent-text(accent-11)/bg 6.15, /accent-bg-subtle 5.50; positive 5.56 (bg 5.08); negative 5.91 (bg 5.32); error 5.51; success 5.05; warning 5.32; info 5.26. Non-text: focus ring 4.77, control border 3.45 (>=3). All >=4.5 text.
VERDICT: PASS
### DW-2.3
PREMISE: Semantic aliases resolved; type scale --text-xs..--text-4xl present; functional colors defined.
EVIDENCE: --background, --surface, --text, --accent-solid (overridden to accent-10), --positive, --negative all defined; --text-xs..--text-4xl present; error/success/warning/info text+bg defined.
VERDICT: PASS

## Edge cases
- Red accent failing AA with white: step 9 (3.81) replaced by accent-10, 4.88:1. Handled.
- Red vs error collision: handled by form (bg container + 4px border + X icon + "Error:" wording), data-direction never red, data-source-down uses amber. Meets "icon + wording" option. Handled.

**All requirements met:** YES

**Verdict: PASS**
