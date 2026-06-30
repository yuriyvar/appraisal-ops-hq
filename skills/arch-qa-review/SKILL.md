---
name: arch-qa-review
description: Run a combined architecture review and QA test pass on a build (a script, module, renderer, adapter, or skill) before it's relied on or built upon. Use whenever the user says "arch review", "QA this", "review the build", "test the build", "/bob-arch-qa-review", or asks whether a piece of the pipeline is solid enough to build on. Produces a written report in code-reviews/ (Summary · Positives · Must/Should/Nice findings · QA results table · prioritized recommendations), fixes cheap real defects in place, and verifies the fixes. Honors the Samurai/katana rule — no cut corners — and the one-session git rule (review-only; never commits).
---

# Arch + QA Review ("/bob-arch-qa-review")

Two passes on one build: an **architecture review** (is it designed right?) and a
**QA test pass** (does it actually behave?). The point is to certify a build
before B/C/D are stacked on it, and to fix the cheap real defects on the spot
rather than just listing them. COWORK_AGENT does the analysis, runs real tests, and
applies fixes; nothing is committed (one-session git rule — review-only).

## Inputs
- The target build (path to the script/module/skill under review).
- Its contract: the schema/spec it implements, the relevant ADR(s), and the
  handoff/build-order entry that defines what it's for.
- A test fixture if one exists (e.g. an `*.example.json`).

## Procedure

1. **Ground in the contract (genchi genbutsu).** Read the target's code, its
   README, the schema it consumes/produces, the governing ADR, and the handoff
   line that specifies it. Note what is *intentionally* out of scope so you
   don't flag a deliberate omission as a defect.

2. **Architecture pass.** Assess against these axes and write findings:
   - **Determinism & side effects** — same input → same output? Hidden I/O,
     network, clock, or global state? (Pipeline renderers/adapters must be
     deterministic and offline unless the contract says otherwise.)
   - **Dependencies** — stdlib-only where it should be? Any pip surface justified?
   - **Separation of concerns** — one responsibility per unit; easy to extend.
   - **Coupling & desync risk** — are two things that must agree bound together,
     or can they drift silently (e.g. parallel lists keyed by display strings)?
   - **Schema/contract fidelity** — every contract field handled; null-safe;
     version/shape guarded.
   - **Domain correctness** — does it encode the appraisal rules? (closed vs
     active/pending segregation, single-source-GLA, county-tagging, the human
     review gate / never-auto-submit, unverified-GLA flagging.)
   - **Security** — output escaping; URL-scheme safety (no `javascript:`/`data:`
     into `href`); no secrets; no client data leaking into the repo.

3. **QA pass — run real tests, don't assert from reading.** At minimum:
   - **Determinism:** render/run twice, compare bytes (hash).
   - **Edge inputs:** empty object, missing required sections, empty arrays,
     null-heavy records — must degrade gracefully, no traceback.
   - **Injection/escaping:** put `<script>`, `&"<>`, and a `javascript:` URL in
     string fields; confirm escaped / neutralized in output.
   - **Contract guards:** wrong schema_version (warn + still run), bad JSON and
     missing file (non-zero exit).
   - **Well-formedness:** parse the output (`html.parser` for HTML).
   - **Branch coverage:** craft a synthetic fixture that exercises branches the
     example doesn't (e.g. active comps, photos, geocoded map points).

4. **Fix the cheap real defects in place.** Anything must/should-fix that is low
   risk and low effort — fix it now, then **re-verify** (re-run the failing test;
   if the mount/env is flaky, verify the changed logic in isolation
   sandbox-locally). Leave larger items as written recommendations. This is the
   Samurai rule: a found corner gets uncut, not just noted.

5. **Write the report** to `code-reviews/arch-qa_<target>_<YYYY-MM-DD>.md` using
   the house format:
   - **Summary** (verdict: approved / blocked-until, in one paragraph)
   - **Architecture review:** Positives · Fixed during review · Should-fix · Nice-to-have · Non-issues
   - **QA test results:** a table (`# | Test | Result`)
   - **Prioritized recommendations**
   - **Reviewer notes** (confirm no commits/merges; flag any env quirks)

6. **Log it.** Append a one-line `[done]`/`[learn]` entry to the TOP of
   `vault/00-inbox.md`, and if a real defect pattern emerged, note it for the
   next kaizen retro.

## Rules
- **Review-only. Never commit, merge, or push** — the one-session git rule holds;
  git writes happen on the host with other Cowork sessions closed.
- **Fix only cheap, safe, in-scope defects.** Anything architectural or risky →
  recommend, don't silently rewrite.
- **Re-verify every fix.** A fix you didn't test is a new corner.
- **Don't flag intentional scope decisions as defects** — confirm against the
  contract first.
- **Be honest about the test environment.** If you couldn't run something
  (mount lag, missing tool), say so and state how you verified instead.
