---
name: weekend-pr-review
description: Saturday 9am code review of the appraisal-ops-hq repo's open work
---

Perform an automated code review of the local git repository at `C:\Users\yuriy\VDV Appraisals\appraisal-ops-hq`. This repo is local-only (no GitHub remote), so review the local equivalent of a pull request.

Steps:

1. Open the repo. Determine what needs review:
   - Any local branch that is ahead of `main` (treat each as a PR). For each such branch, get the diff against `main` with: `git diff main...<branch>`.
   - Any uncommitted changes in the working tree (`git status -s`, `git diff`, and untracked files).
   If there is nothing ahead of main and no uncommitted changes, write a short report saying "No open changes to review this week" and stop after step 4.

2. Use the `review` skill / slash command (`/review`) approach to conduct the review. For each diff, assess: correctness and bugs, security issues, error handling, readability and naming, test coverage, and adherence to any conventions documented in the repo's CLAUDE.md. Be specific — cite file and line where possible, and distinguish must-fix issues from nice-to-haves.

3. Write the results to a dated markdown file at `C:\Users\yuriy\VDV Appraisals\appraisal-ops-hq\code-reviews\review-<YYYY-MM-DD>.md`. Create the `code-reviews` folder if it doesn't exist. Structure: a one-paragraph summary at top, then a section per branch/changeset, then a prioritized list of recommendations.

4. Present the report file to the user with present_files and give a 2-3 sentence summary of the most important findings.

Do NOT commit, push, merge, or modify any code — this is review-only. Only create the review report file.