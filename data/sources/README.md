# Curated source snapshots

See [the data guide](../README.md) for inventory, provenance, source terms,
offline verification, and the contribution policy.

The `baseline/2026-09-26/` and `historical/2026-09-26/` directories preserve
original downloaded bytes. `archive.json` points to each authoritative source
manifest and records when the archive copy was fetched and verified. Existing
model/data semantics are unchanged by adding these copies.

Do not open and resave source spreadsheets or normalize source CSV line endings.
Make a working copy under ignored `data/raw/` or `data/processed/` for exploration.
Use a new snapshot directory for an intentional source revision.
