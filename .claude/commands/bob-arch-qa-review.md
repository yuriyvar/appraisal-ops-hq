Run a combined architecture review and QA test pass on the build named in the
arguments (or, if none given, the most recent build from this session / the
handoff). Use the arch-qa-review skill (skills/arch-qa-review/SKILL.md):

1. Ground in the contract — read the target's code, README, the schema/spec it
   implements, the governing ADR, and the handoff/build-order line that defines
   it. Note anything intentionally out of scope.
2. Architecture pass — determinism & side effects, dependencies, separation of
   concerns, coupling/desync risk, schema fidelity, domain correctness
   (closed-vs-active comps, single-source GLA, human review gate), security
   (output escaping, URL-scheme safety, no client data in repo).
3. QA pass — RUN real tests: determinism (byte-compare), edge inputs (empty /
   missing / null-heavy), injection/escaping, contract guards (bad version, bad
   JSON, missing file), output well-formedness, and a synthetic fixture for
   branches the example misses.
4. Fix cheap, safe, in-scope defects IN PLACE and re-verify each (Samurai rule —
   no cut corners). Leave larger items as recommendations.
5. Write code-reviews/arch-qa_<target>_<date>.md in the house format (Summary /
   Positives / Fixed / Should / Nice / Non-issues / QA table / recommendations /
   reviewer notes).
6. Append a one-line entry to the top of vault/00-inbox.md.

Review-only: never commit, merge, or push (one-session git rule). Be honest
about any test that couldn't run and how you verified instead.
