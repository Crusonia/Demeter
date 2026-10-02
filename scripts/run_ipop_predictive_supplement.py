"""Launch the frozen aggregate replay after checking a fresh output destination."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

import replay_ipop_predictive_supplement as frozen_replay

FROZEN_COMMIT = "6210db409e890ef3811afc1c01282d232e4a1dd7"


def _probe_hard_links(temporary: Path, parent: Path) -> None:
    """Check final publication support using a reserved, unique sibling name."""
    descriptor, name = tempfile.mkstemp(prefix=".ipop-link-probe-", dir=parent)
    os.close(descriptor)
    probe = Path(name)
    probe.unlink()
    linked = False
    try:
        os.link(temporary, probe)
        linked = True
    finally:
        # A failed exclusive link may mean another file acquired the name.
        # Remove the probe only if this call successfully created its link.
        if linked:
            probe.unlink()


def run(raw: Path, output: Path, *, freeze_commit: str = FROZEN_COMMIT) -> None:
    """Preflight publication before replay; publish atomically without replacement.

    The temporary file is reserved in the destination directory before any
    source access or fitting. A hard link publishes the finished bytes only if
    the final name is still unused, including if another process created it
    during replay. Only this launcher's temporary file is removed on failure.
    """
    if freeze_commit != FROZEN_COMMIT:
        raise ValueError("The supported frozen replay identity is required")
    output = Path(output)
    if os.path.lexists(output):
        raise ValueError("A fresh output destination is required")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        descriptor, name = tempfile.mkstemp(prefix=".ipop-predictive-", dir=output.parent)
        temporary = Path(name)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            # Verify writable publication storage before the expensive replay.
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
            _probe_hard_links(temporary, output.parent)
            if os.path.lexists(output):
                raise ValueError("A fresh output destination is required")
            result = frozen_replay.replay(Path(raw), freeze_commit=freeze_commit)
            encoded = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
            handle.seek(0)
            handle.truncate()
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        # Unlike replace/rename, link cannot overwrite a concurrently created file.
        os.link(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--freeze-commit", default=FROZEN_COMMIT)
    args = parser.parse_args(argv)
    try:
        run(args.raw, args.output, freeze_commit=args.freeze_commit)
    except Exception:
        # Never print cache paths, source tokens, or private exception payloads.
        print("Supplement unavailable: fresh output preflight or frozen replay failed")
        return 1
    print("Completed additive aggregate supplement; original reports and engine gates preserved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
