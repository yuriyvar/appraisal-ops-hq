<#
.SYNOPSIS
    Fixes the corrupted .git/config left by the 2026-06-13 concurrent-session crash,
    then stages and commits all pending changes.

.NOTES
    Run from repo root with ONE Cowork session open (this one).
    Usage: powershell -ExecutionPolicy Bypass -File scripts\git-fix-and-commit.ps1

    REQUIRED: fill in GITHUB_REMOTE_URL below before running.
#>

$ErrorActionPreference = "Stop"
$repoRoot = "C:\Users\yuriy\VDV Appraisals\appraisal-ops-hq"

# ── EDIT THIS ────────────────────────────────────────────────────────────────
$GITHUB_REMOTE_URL = "https://github.com/YOUR-USERNAME/appraisal-ops-hq.git"
# ─────────────────────────────────────────────────────────────────────────────

Set-Location $repoRoot

Write-Host "Step 1 — Removing stale lock files..." -ForegroundColor Cyan
$locks = @(".git\HEAD.lock", ".git\config.lock", ".git\index.lock")
foreach ($lock in $locks) {
    if (Test-Path $lock) {
        Remove-Item $lock -Force
        Write-Host "  Removed $lock"
    } else {
        Write-Host "  $lock not found (ok)"
    }
}

Write-Host "`nStep 2 — Recreating .git\config..." -ForegroundColor Cyan
$gitConfig = @"
[core]
	repositoryformatversion = 0
	filemode = false
	bare = false
	logallrefupdates = true
	symlinks = false
	ignorecase = true
	autocrlf = false
[remote "origin"]
	url = $GITHUB_REMOTE_URL
	fetch = +refs/heads/*:refs/remotes/origin/*
[branch "main"]
	remote = origin
	merge = refs/heads/main
[user]
	name = Yuriy Varvashenya
	email = y.varvashenya@gmail.com
"@
Set-Content -Path ".git\config" -Value $gitConfig -Encoding UTF8
Write-Host "  .git\config written."

Write-Host "`nStep 3 — Verifying git status..." -ForegroundColor Cyan
git status

Write-Host "`nStep 4 — Staging all changes..." -ForegroundColor Cyan
git add -A

Write-Host "`nStep 5 — Committing..." -ForegroundColor Cyan
$msg = @"
feat: property-search v2 + git setup docs (2026-06-13 sessions)

- skills/property-search/SKILL.md: v2 — automated MLS# lookup via
  Zillow JS + Matrix, full DM import via computer use, Comps files
  path, builder-sale handling, ArcGIS TaxID Double fix, luxury GLA
  band, Matrix MAP-tab radius rule
- skills/property-search/archived/SKILL-v1.md: archive of v1 before
  automation enhancements
- vault/00-inbox.md: 2026-06-13 session learnings (Chesterfield
  UseCode map, StyleCraft builder-direct, Zillow new-construction
  parcel mismatch, MLS# JS extraction, TaxID Double precision,
  Comps files folder, Matrix one-session rule, Henrico assessment)
- vault/20-standard-work/SOP-order-intake.md: add Comps files path
- skills/property-search/references/va-data-sources.md: Chesterfield
  live FeatureServer endpoint + new-construction condo quirk
- docs/git-setup.md: first-time Git setup + concurrent-session rules
- scripts/git-fix-and-commit.ps1: this script (self-documenting)

Fixes: corrupted .git/config from concurrent Cowork session crash
"@
git commit -m $msg

Write-Host "`nStep 6 — Pushing to origin/main..." -ForegroundColor Cyan
git push origin main

Write-Host "`nDone. Run 'git log --oneline -5' to verify." -ForegroundColor Green
