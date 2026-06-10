# scripts/

Small standalone utilities. Rules: Python 3, stdlib-first, each script has a
docstring with usage, and anything touching client files runs OUTSIDE the repo
tree (pass paths as arguments).

Planned (see BACKLOG.md):
- new_job_folder.py — create the standard job folder structure from an address
- metrics_rollup.py — append a weekly row to vault/50-metrics/metrics.md from inputs
