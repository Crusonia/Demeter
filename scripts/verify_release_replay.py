"""CI replay in a separately extracted source tree using the current locked environment."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source, bundle, output = args.source.resolve(), args.bundle.resolve(), args.output.resolve()
    # CI creates this trusted snapshot itself. Verification alone never executes ZIP code.
    env = dict(os.environ, PYTHONPATH=str(source / "src"), PYTHONUTF8="1")
    loaded = subprocess.check_output(
        [sys.executable, "-c", "from demeter.releases import source_root; print(source_root())"],
        cwd=source,
        env=env,
        text=True,
        encoding="utf-8",
    ).strip()
    if Path(loaded).resolve() != source:
        raise ValueError(f"Replay imported the wrong source checkout: {loaded}")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "demeter.cli",
            "release",
            "replay",
            str(bundle),
            "--output",
            str(output),
        ],
        cwd=source,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    report = json.loads(output.read_bytes())
    if not report["passed"]:
        raise ValueError("Extracted-source replay failed")
    print(
        json.dumps(
            {"passed": True, "comparisons": report["comparisons"], "source": str(source)}, indent=2
        )
    )


if __name__ == "__main__":
    main()
