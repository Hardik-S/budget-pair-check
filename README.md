# Budget Pair Check

Budget Pair Check validates already-normalized token-usage receipts before a developer compares paired single-agent and team-agent runs. It checks task/model/harness/replicate identity, complete pairs, required token counts, and a shared declared token cap. It does not run agents, collect usage, price tokens, or claim benchmark superiority.

```powershell
python -m pip install -e ".[dev]"
budget-pair-check analyze examples/manifest.json examples/runs.json --format text
```

Included data will be synthetic. Do not put private or sensitive run receipts into public examples.
