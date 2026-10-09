# Budget Pair Check v0.1.0 launch note

**Problem:** when comparing single-agent and team-agent coding runs, missing usage counts, incomplete pairs, mismatched task/model/harness identities, or inconsistent token caps can make the comparison unreliable.

**Reproduce:** install in a fresh Python 3.10+ environment, then run:

```console
python -m pip install .
budget-pair-check analyze examples/manifest.json examples/runs.json --format json
```

**Synthetic result:** the included 2-task × 2-replicate example reports 4 runs per condition, 570 single-condition tokens and 810 team-condition tokens, and paired outcomes of 1 both-pass, 1 both-fail, 1 single-only-pass, and 1 team-only-pass.

**Technical finding:** the offline validator rejects incomplete or mismatched receipt matrices, malformed task hashes, missing or non-integer token counts, over-cap runs, duplicate JSON keys, and nonstandard non-finite JSON values before reporting descriptive totals.

**Limits:** examples are synthetic. The tool validates supplied receipts; it does not collect or attest usage, run agents or code, estimate price, measure collaboration quality, or establish causality, generalization, or benchmark superiority.
