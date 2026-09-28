# Engineering baseline checkpoint: 0.1.0a1 / e969c41

**Validation-only. Clinical parameter fitting remains deferred.**

- [Complete canonical baseline](baseline.json)
- [Generating-commit, source/evidence and replay receipt](receipt.json)
- [Model card copied from the full bundle](MODEL_CARD.md)

This directory is a baseline archive, **not a complete release bundle**. The
model card's `results/` references refer to the full generated bundle. Its
generating commit is
[`e969c41ea908ccde153f343cc66f65a7826c1884`](https://github.com/Crusonia/Demeter/commit/e969c41ea908ccde153f343cc66f65a7826c1884).
The later commit adding this receipt must not be confused with the generating
source. Exact baseline/card bytes are registered in the data package inventory.

The clean-source run used 128 paired uncertainty draws, 64 Sobol base samples and
seed 42. All seven canonical calculations matched on replay from a separately
extracted source tree using the same locked Windows environment. Only historical
Git-location metadata was excluded. Sample counts and exact reproduction do not
establish convergence, clinical validity or independent scientific review.

To reconstruct the full bundle, check out that generating commit in a separate
directory and run:

```text
uv sync --locked
uv run demeter release build outputs/reproduced --draws 128 --samples 64 --seed 42
uv run demeter release verify outputs/reproduced
```

Follow the bundle's `REPRODUCE.md` for extraction and replay. New timestamps and
runtime inventories can change the overall manifest hash; use the result
comparison tolerances documented in [the release policy](../../../docs/RELEASES.md).
The original manifest/source ZIP hashes are retained in the receipt. For a
published result, retain the entire original bundle, not just this baseline.
