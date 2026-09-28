"""Execute the trusted repository learning notebook without a notebook server."""

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks/learning_path.ipynb"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, default=Path("outputs/tutorial"))
    args = parser.parse_args()
    destination = args.destination.resolve()
    # Notebook code is project code, like running a Python script. No untrusted input.
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    namespace = {"__name__": "__main__", "TUTORIAL_DESTINATION": destination}
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    count = 0
    for cell in notebook["cells"]:
        if cell["cell_type"] == "code":
            code = compile("".join(cell["source"]), f"{NOTEBOOK}:{cell['id']}", "exec")
            exec(code, namespace)
            count += 1
    print(f"Executed {count} code cells; all lesson assertions passed. Outputs: {destination}")


if __name__ == "__main__":
    main()
