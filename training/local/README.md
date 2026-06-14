# Local training harness

Fast iteration loop that mirrors `.github/workflows/train.yml` step-for-step, so
training-script changes get validated on your own machine before a full CI run.

Runs in WSL Ubuntu against the patched Tesseract (NoMercy fork, append-index fix)
installed at `$HOME/tesseract-install` — the same prefix CI builds on beast-unit.

## One-time setup

```bash
wsl -d Ubuntu-24.04
cd /mnt/c/Projects/NoMercy/packages/nomercy-tesseract
bash training/local/setup-wsl.sh
```

Builds Tesseract with training tools. Idempotent — re-running is a no-op once built.

## Smoke run

```bash
LANG_CODE=swe MAX_ITERATIONS=400 MAX_LINES=200 bash training/local/run-train.sh
```

Output lands in `training/local/out/$LANG_CODE.traineddata`. This path is
git-ignored and never overwrites the shipped model in `tessdata/` — CI is the only
path that writes and commits `tessdata/`.

| Knob | Default | Purpose |
|------|---------|---------|
| `LANG_CODE` | — | language to train (must exist in `tessdata_best`) |
| `MAX_ITERATIONS` | 400 | tiny for a smoke run; raise to confirm convergence |
| `MAX_LINES` | 200 | ground-truth lines to render |

## Promote to CI

Once a change looks right locally, push and dispatch the full run:

```bash
gh workflow run train.yml -f languages="swe,nor,pol,..." -f max_iterations=100000
```
