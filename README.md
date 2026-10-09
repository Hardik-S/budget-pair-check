# Budget Pair Check

Budget Pair Check is an offline validator for already-normalized token-usage receipts. It verifies that a single-agent and team-agent run share the same task, model, harness, and replicate; that the declared task × replicate × setting matrix is complete; and that every run includes actual nonnegative input/output token counts within the declared per-run cap.

It reports descriptive totals and paired pass/fail counts. It does not run agents or submitted code, collect usage, access a network, convert tokens to prices, or make benchmark, causal, or superiority claims. Public examples contain synthetic data only.

## Quickstart

Requires Python 3.10 or newer. From a fresh virtual environment, install the package and run the included synthetic receipt pair:

```console
python -m pip install .
budget-pair-check analyze examples/manifest.json examples/runs.json --format text
```

The same command is available as `python -m budget_pair_check`. Add `--format json` for machine-readable output. Invalid or incomplete input prints an actionable diagnostic and exits with status 2; valid input exits 0.

## Validate your own receipts

The manifest declares version 1, settings `single` and `team`, a positive `budget_cap_tokens`, tasks with IDs and SHA-256 hashes, and a nonempty list of replicate IDs. The runs document declares version 1 and one row for each task × replicate × setting cell. Each row includes a unique run ID, the task ID and matching hash, setting, replicate, model, harness, exact nonnegative integer input/output token counts, a boolean test result, and a local evidence label. Each single/team pair must use the same model and harness.

The analyzer rejects incomplete or duplicate cells, unknown IDs, mismatches, missing counts, booleans/floats/negative token counts, over-cap runs, duplicate JSON keys, and nonstandard `NaN`/`Infinity` values. It does not inspect evidence files or verify that token counts came from a provider.

Run the tests with `python -m pip install -e ".[dev]"` followed by `python -m pytest`.
