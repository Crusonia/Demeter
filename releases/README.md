# Engineering checkpoints

`profile.yaml` declares version/compatibility and canonical run scope for the
[release workflow](../docs/RELEASES.md). It does not grant scientific acceptance.

The archive records complete canonical baseline outputs against an exact earlier
source commit, with its evidence/source hashes and model card. Referencing a
prior commit avoids a self-referential checksum: the archive commit may add
receipts, but the recorded generating commit is the one to reproduce.

Full bundles include all canonical analyses and exact source/data snapshots;
generate them with `demeter release build`. Their default location is ignored
`outputs/releases/`. Preserve the complete bundle for any published result.
CI artifacts have limited retention and do not replace a permanent release archive.

All current checkpoints are validation-only. No clinical calibration, independent
scientific acceptance or final v0.1 release is implied by an archived baseline.
