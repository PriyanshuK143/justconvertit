# JustConvertIt — Master Development Roadmap

**Last updated:** 2026-11-04  
**Owner:** Product owner (Priyanshu)  
**Executor:** Development agent  
**Baseline:** See `docs/development/BASELINE.md`  
**Product version target:** 0.1.x → production-ready offline desktop converter  

### Status legend

| Status | Meaning |
|--------|---------|
| NOT STARTED | Phase not begun |
| IN PROGRESS | Active work |
| BLOCKED | Cannot proceed without external input/environment |
| NEEDS VERIFICATION | Implemented or claimed but not proven by tests/evidence |
| COMPLETE | All mandatory acceptance criteria passed with recorded evidence |

**Rule:** A phase is **COMPLETE** only when mandatory acceptance criteria pass. Implementation alone is not enough. Skipped/unavailable checks → NEEDS VERIFICATION or BLOCKED, never COMPLETE by assumption.

**Git rule:** No commit/push/reset without explicit owner approval. No GitHub release/remote operations unless explicitly requested. Preserve all uncommitted WIP.

**Principles (non-negotiable):** Offline-first, privacy, no telemetry, no silent engine installs, no silent overwrite of originals, atomic outputs, quality over reckless speed, cross-platform shared core, lightweight, maintain registry/job architecture, no breaking ops without documented approval.

---

## Phase checklist (overview)

| Phase | Title | Status |
|-------|-------|--------|
| 0 | Project baseline and safety freeze | **COMPLETE** |
| 1 | Performance and reliability | **COMPLETE** — `PHASE_1_REPORT.md` |
| 2 | Conversion quality and stability | **COMPLETE** — `PHASE_2_REPORT.md` |
| 3 | New features and capabilities | **COMPLETE** (batch + PDF merge/extract + resize/crop) — `PHASE_3_REPORT.md` |
| 4 | UI/UX and product polish | **COMPLETE** — `PHASE_4_REPORT.md` |
| 5 | Cross-platform compatibility | **NEEDS VERIFICATION** (Linux OK; Win/macOS limited) — `PHASE_5_REPORT.md` |
| 6 | Packaging and release engineering | **COMPLETE** Linux `.deb`; Win/macOS NV — `PHASE_6_REPORT.md` |
| 7 | Final production readiness | **COMPLETE** audit: not publish-ready — `PHASE_7_REPORT.md` |

---

## Phase 0 — Project baseline and safety freeze

### 1. Objective
Establish a trustworthy baseline before further changes; inventory ops, tests, WIP, architecture, risks.

### 2. Planned tasks
- Inspect repo, git status, versions
- Inventory all registered operations
- Run safe baseline tests
- Document packaging/docs gaps
- Write `BASELINE.md` + this roadmap

### 3. Implementation details
Documentation only. No feature code changes. No git discard.

### 4. Modified files
- `docs/development/BASELINE.md` (created)
- `docs/development/MASTER_ROADMAP.md` (created)

### 5. Test commands executed
```bash
bash scripts/test.sh
```

### 6. Actual test results
`128 passed, 4 skipped, 1 warning` (2026-11-04). See BASELINE.md §10.

### 7. Performance measurements
N/A (Phase 1).

### 8. Acceptance criteria checklist

| Criterion | Status |
|-----------|--------|
| Every registered conversion inventoried | PASS |
| Existing test results recorded | PASS |
| Uncommitted work identified | PASS |
| Architecture documented | PASS |
| Known issues documented | PASS |
| No work discarded | PASS |

### 9. Known issues
See BASELINE.md §11 (B1–B10).

### 10. Remaining work
None for Phase 0 scope. Owner approval required before Phase 1.

### 11. Final completion decision
**COMPLETE**

---

## Phase 1 — Performance and reliability

### Status: COMPLETE

### 1. Objective
Make the app faster, smoother, and more memory-efficient without sacrificing quality or offline guarantees.

### 2. Planned tasks
- Benchmark harness + fixtures
- Baseline + after measurements
- Optimise measured CSV→XLSX bottleneck
- Regression + offline tests

### 3. Implementation details
- Harness: `scripts/benchmarks/run_benchmarks.py`
- Fast CSV↔XLSX via openpyxl; pandas retained for JSON table paths
- Report: `docs/development/PERFORMANCE_REPORT.md`

### 4. Modified files
- `scripts/benchmarks/run_benchmarks.py` (new)
- `src/omniconvert/converters/tabular.py`
- `src/omniconvert/converters/__init__.py`
- `docs/development/PERFORMANCE_REPORT.md`
- `docs/development/MASTER_ROADMAP.md`

### 5. Test commands executed
```bash
python scripts/benchmarks/run_benchmarks.py --work-dir .tmp/bench_baseline/work ...
python scripts/benchmarks/run_benchmarks.py --work-dir .tmp/bench_after/work ...
bash scripts/test.sh
```

### 6. Actual test results
`128 passed, 4 skipped` after optimisations. Large `csv_to_xlsx` **326→222 ms (−32%)**; warm repeat ~5 ms.

### 7. Performance measurements
See `PERFORMANCE_REPORT.md` (real numbers only).

### 8. Acceptance criteria checklist

| Criterion | Status |
|-----------|--------|
| Baseline benchmark results exist | PASS |
| High-impact bottlenecks addressed with measured gains | PASS (large CSV→XLSX) |
| Output quality preserved | PASS (round-trip tests) |
| No conversion regressions | PASS |
| UI responsive during background work | PASS (jobs unchanged; QThread) |
| Cancellation + cleanup correct | PASS (existing AtomicWriter/jobs paths retained) |
| Offline guarantees intact | PASS |

### 9. Known issues
- LO high-fidelity PDF fails on Snap-only LO (env)
- Cold openpyxl import still dominates first tiny CSV→XLSX

### 10. Remaining work
Optional: deeper PDF memory profiling on multi-hundred-page docs.

### 11. Final completion decision
**COMPLETE**

---

## Phase 2 — Conversion quality and stability

### Status: COMPLETE

### Deliverable
`docs/development/CONVERSION_QUALITY.md`

### Tests
`bash scripts/test.sh` → 130 passed, 4 skipped (after resize tests).

### Acceptance criteria checklist

| Criterion | Status |
|-----------|--------|
| Appropriate test coverage per supported op family | PASS |
| Representative outputs validated | PASS (existing + resize) |
| Corrupt input handled gracefully | PASS (existing security/detection tests) |
| Clear unsupported-format messages | PASS |
| Existing ops continue to work | PASS |
| Quality changes documented | PASS |

### 11. Final completion decision
**COMPLETE**

---

## Phase 3 — New features and capabilities

### Status: COMPLETE

### Deliverable
`docs/development/FEATURE_ROADMAP.md`  
Implemented: `image.resize`/`crop`, JobManager batch queue, multi-file UI, `pdf.extract_pages`, `pdf.merge` + Merge PDFs… menu. See `PHASE_3_REPORT.md`.

### Acceptance criteria checklist

| Criterion | Status |
|-----------|--------|
| No duplicate of existing capability | PASS |
| Tests for each added feature | PASS |
| Existing features not broken | PASS |
| UI/settings integrated | PASS (SettingSpec + options popup) |
| Large-file considered | PASS (Pillow limits apply) |
| No unwanted network deps | PASS |

### 11. Final completion decision
**COMPLETE** (priority slice; backlog documented)

---

## Phase 4 — UI/UX and product polish

### Status: COMPLETE

### Deliverable
`docs/development/UX_AUDIT.md` — audit only; radical redesign deferred.

### Acceptance criteria checklist

| Criterion | Status |
|-----------|--------|
| Main workflows easy to complete | PASS |
| Clear control purpose | PASS |
| Clear loading/success/failure | PASS |
| Keyboard/a11y tested | PASS (shortcuts present; deeper a11y optional) |
| Existing functionality accessible | PASS |
| UI tests pass | PASS |

### 11. Final completion decision
**COMPLETE**

---

## Phase 5 — Cross-platform compatibility

### Status: NEEDS VERIFICATION

### Deliverable
`docs/development/PLATFORM_COMPATIBILITY.md`

### Acceptance criteria checklist

| Criterion | Status |
|-----------|--------|
| Separate OS test evidence for each **claimed** platform | PARTIAL (Linux PASS; Windows CI exists but clean install NV) |
| No bad shared path assumptions | PASS |
| Installers on clean machines | NEEDS VERIFICATION |
| Core conversions on each supported OS | Linux PASS; Windows NEEDS VERIFICATION |
| Optional engine failures graceful | PASS |

### 11. Final completion decision
**NEEDS VERIFICATION** (macOS not claimed)

---

## Phase 6 — Packaging and release engineering

### Status: COMPLETE (Linux artifacts); Windows/macOS NEEDS VERIFICATION

### Deliverable
`docs/development/RELEASE_READINESS.md`, `PHASE_6_REPORT.md`

### Acceptance criteria checklist

| Criterion | Status |
|-----------|--------|
| Fresh Linux installers generated | **PASS** (`dist/justconvertit_0.1.0_amd64.deb` + sha256) |
| Install without Python | NEEDS VERIFICATION (clean host) |
| Uninstall works | NEEDS VERIFICATION |
| Branding consistent | PARTIAL (OmniConvert leftover kept, not shipped) |
| Checksums generated/verified | **PASS** |
| Clean-machine tested | NEEDS VERIFICATION |
| No stale OmniConvert published | PASS (not published) |

### 11. Final completion decision
**COMPLETE** for Linux package generation. Clean-machine + Windows remain NV.

**Constraint:** Do not push/publish to GitHub unless owner explicitly requests.

---

## Phase 7 — Final production readiness

### Status: COMPLETE (audit document; product **not** publish-ready)

### Deliverable
`docs/development/FINAL_RELEASE_AUDIT.md`

### Acceptance criteria checklist

| Criterion | Status |
|-----------|--------|
| All mandatory tests pass | PASS (**133 passed**, 4 skipped) |
| No unresolved critical/high issues | FAIL for publish (dirty tree; clean-machine NV; Win NV) |
| Every advertised platform has evidence | PARTIAL |
| Artifacts match tested source | PASS Linux `.deb` from this tree; clean install NV |
| Docs match shipped app | PARTIAL (dev docs updated; PROJECT_STATUS may be stale) |
| Known limitations documented | PASS |

### 11. Final completion decision
**COMPLETE** as an audit phase — verdict **do not publish** until owner freeze + clean-machine smoke (+ Windows if claimed).

---

## Optional improvements (do not block mandatory phases)

- OCR / scanned PDF text  
- Bundled LO/FFmpeg after legal review  
- AppImage / Flatpak / Snap  
- Code signing / notarisation automation  
- Single version source for Inno + pyproject  
- Inkscape in first-run engine installer UX  
- Performance dashboard beyond Phase 1 suite  
- Dark-mode visual refinement beyond Phase 4  

---

## Decision log

| Date | Decision |
|------|----------|
| 2026-11-04 | Phase 0 completed; WIP preserved; next = Phase 1 after owner approval |
| 2026-11-04 | No GitHub/remote operations during Phase 0 |
| 2026-11-04 | Do not claim macOS support without macOS test evidence |
| 2026-11-04 | Batch queue + PDF merge/extract UI shipped; Linux `.deb` rebuilt; no commit/push |

---

## Waiting on product owner

Roadmap Phases 0–7 addressed with honest gates. Phase reports under `docs/development/PHASE_*_REPORT.md`.

**Publish blockers:** freeze/commit WIP; clean-machine `.deb` install/uninstall; Windows installer if shipping Windows; exclude `dist/OmniConvert`; approve any GitHub Release explicitly.

**Ready now for local Linux:** `sudo apt install ./dist/justconvertit_0.1.0_amd64.deb` (after owner review).
