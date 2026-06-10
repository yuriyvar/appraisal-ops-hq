---
sop: SOP-order-intake
version: 0.1
effective: 2026-06-10
owner: Operations
last-kaizen: —
andon-count: 0
---

# SOP-order-intake (v0.1)

**Purpose:** every new order reaches "ready to schedule" state with zero missing data.
**Trigger:** order email/portal notification received.
**Takt expectation:** <= 15 min touch-time per order.

## Steps (draft — refine in Sprint 1)
1. Save engagement letter / order PDF to the job folder in the client jobs folder (path in CLAUDE.md Environment) (naming: YYYY-MM-DD_address_client).
2. Extract: address, client/AMC, loan #, product type, fee, due date, special instructions.
3. Check 10-notes/ for client-specific preferences (e.g. [[northstar-eta-preference]]).
4. Create job record; pull county assessor card + FEMA flood zone + prior 3-yr sale history.
5. Confirm receipt to client; flag scheduling.

## Quality checks (jidoka)
- Missing legal description or conflicting address -> STOP, andon, contact client before proceeding.
- Due date < 5 business days -> escalate to scheduler same hour.

## Change log
- v0.1 (2026-06-10): initial standard, drafted from current informal practice.
