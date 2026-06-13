# Git Setup — appraisal-ops-hq

**Machine:** Yuriy's primary workstation (Windows)  
**Repo path:** `C:\Users\yuriy\VDV Appraisals\appraisal-ops-hq\`  
**Remote:** GitHub (private) — see step 3 for URL  
**Last updated:** 2026-06-13

---

## First-time setup (new machine or fresh Git install)

### 1. Install Git for Windows
Download from https://git-scm.com/download/win — use all defaults except:
- **Default editor**: change from Vim to anything you prefer (VS Code, Notepad++)
- **Line endings**: select "Checkout as-is, commit as-is" (repo already has
  `core.autocrlf = false` — don't let Git rewrite line endings)

Verify: open **Git Bash** (Start → Git Bash) and run `git --version`.

### 2. Set global identity (one-time per machine)
```bash
git config --global user.name "Yuriy Varvashenya"
git config --global user.email "y.varvashenya@gmail.com"
git config --global core.autocrlf false
git config --global init.defaultBranch main
```

### 3. Authenticate to GitHub
Easiest: use the **GitHub CLI** (`winget install GitHub.cli`) then run `gh auth login`.  
Alternative: create a Personal Access Token at https://github.com/settings/tokens
(scope: `repo`) and use it as your password when Git prompts.

### 4. Fix the corrupted repo (one-time — do this before anything else)
The `.git/config` was zeroed during a concurrent Cowork session crash (see andon
in `vault/00-inbox.md`). Run the script at `scripts/git-fix-and-commit.ps1` from
a PowerShell prompt **with no other Cowork sessions open**:

```powershell
cd "C:\Users\yuriy\VDV Appraisals\appraisal-ops-hq"
powershell -ExecutionPolicy Bypass -File scripts\git-fix-and-commit.ps1
```

The script will:
- Delete the three stale `.git/*.lock` files
- Recreate `.git/config` with the correct remote URL
- Stage and commit all pending changes from the 2026-06-13 sessions

### 5. Verify
```bash
git log --oneline -5
git status
git remote -v
```

---

## Day-to-day rules (from CLAUDE.md)

- **One Cowork session at a time** when writing to the repo. Concurrent sessions
  can corrupt `.git/config` (happened 2026-06-13).
- **Branch naming**: `kaizen/K-NNN-*` for SOP changes, `feat/*` for new
  skills/scripts/MCP, `fix/*` for corrections.
- **No secrets in the repo.** API keys in untracked `.env` files only.
- **No client/order data in the repo.** Those live in
  `C:\Users\yuriy\VDV Appraisals\` (never copied here).
- Claude commits on `feat/*` branches; Yuriy merges to `main` via PR.

---

## Cloning on a new machine
```bash
git clone https://github.com/YOUR-USERNAME/appraisal-ops-hq.git \
  "C:\Users\yuriy\VDV Appraisals\appraisal-ops-hq"
```
Never copy the folder through OneDrive — always clone fresh.
