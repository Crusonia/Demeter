"""Distribution builds carry the same static UI that the local launcher serves."""

import importlib.util
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        if version == "editable":
            return
        root = Path(self.root)
        spec = importlib.util.spec_from_file_location(
            "explorer_build", root / "scripts/build_explorer.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assets = module.build(root)
        if self.target_name == "wheel":
            build_data["force_include"][str(assets)] = "demeter/explorer/static"
