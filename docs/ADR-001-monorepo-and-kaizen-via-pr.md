# ADR-001: Monorepo with kaizen-via-pull-request

Date: 2026-06-10 · Status: accepted

## Decision
One private repo holds the knowledge vault, skills, commands, MCP servers, and
scripts. SOP changes are made only on kaizen/* branches and merged by a human.

## Rationale
- Knowledge and automation version together: an SOP change and the skill change
  that implements it ship in one commit.
- Git supplies the TPS controls for free: protected main = standard work,
  PR review = jidoka human pull-cord, git log = SOP change history,
  tags = sprint boundaries.
- Plain markdown keeps the vault portable (Obsidian, Cowork, any editor).

## Consequences
- Client PII must be strictly excluded (.gitignore + CLAUDE.md rule 1).
- Team needs minimal Git literacy for approvals; mitigated by GitHub's web UI
  and Claude preparing all branches.

## Revisit when
Vault exceeds ~2k notes, or non-Git users need to author SOPs directly.
