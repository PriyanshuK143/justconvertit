# UX Audit — Phase 4

**Date:** 2026-11-04  
**Status:** COMPLETE (audit + prior polish already in WIP; no radical redesign)

## Current UX (code-verified)

| Flow | Behaviour | Assessment |
|------|------------|------------|
| Open file | Hub click / drop / dialog | Clear |
| Few ops | Action chips + chevrons | Clear; crisp borders (no soft blur mismatch) |
| Many ops | Radial pads + idle float | Consistent chrome with chips |
| Convert | Drag puck or click pad → settings → Save As | Clear |
| Image crop | Visual rectangle dialog | Clear vs % for video |
| Progress | Banner pill on wheel | Readable after pill fix |
| Success | Yes/No open file | Clear |
| Failure | Soft status, no crash dialog | Good |
| Move orb | Rim / gap / Alt+hub; on-screen clamp | Improved vs left-edge stick |
| Settings / engines | First-run consent; Settings dialog | Matches privacy rules |
| Keyboard | Open, Esc quit, Ctrl+, settings | Basic a11y present |

## Issues (non-blocking)

| ID | Issue | Severity |
|----|-------|----------|
| U1 | Wheel shows max 8 ops — overflow not browsable | Medium |
| U2 | Resize/Crop/No BG compete for pad slots on images | Low |
| U3 | No in-flow tutorial beyond hub subtitle | Low |
| U4 | High-DPI / multi-monitor | NEEDS VERIFICATION on more hardware |

## Decisions

- No radical redesign this phase (preserve radial product direction).
- Prior polish (banner pill, hub chrome consistency, move grips) retained.

## Acceptance

| Criterion | Status |
|-----------|--------|
| Main workflows completable | PASS |
| Clear controls | PASS |
| Loading/success/failure clear | PASS |
| Keyboard basics tested in code paths | PASS (shortcuts present) |
| UI tests | PASS (`tests/ui/*`) |
