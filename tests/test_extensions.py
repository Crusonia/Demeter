from pathlib import Path
import json
import shutil

import pytest
import yaml
from typer.testing import CliRunner

from demeter import extensions as ext
from demeter.cli import app
from demeter.examples.transition_modules import NoDietEffect
from demeter.model import simulate
from demeter.schema import EvidenceRegistry, Scenario

BASE = EvidenceRegistry.from_yaml("evidence/parameters.yaml")
CORE = "demeter.core@1.0.0"
EXPERIMENTS = "demeter.experiments@1.0.0"
COMMUNITY = "community.null@1.0.0"


def write_yaml(path, data):
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8", newline="\n")


@pytest.fixture
def package(tmp_path):
    return Path(shutil.copytree("examples/community_null", tmp_path / "package")) / "package.yaml"


def edit(path, **changes):
    data = yaml.safe_load(path.read_bytes())
    data.update(changes)
    write_yaml(path, data)
    return data


def repin(path, name, text):
    (path.parent / name).write_text(text, encoding="utf-8", newline="\n")
    data = yaml.safe_load(path.read_bytes())
    data["files"][name] = ext.sha256((path.parent / name).read_bytes())
    write_yaml(path, data)


def load(path, tmp_path):
    registry = tmp_path / "registry.yaml"
    ext.register(path, registry)
    return ext.resolve(COMMUNITY, registry)


def overlay(path, data):
    repin(path, "evidence.yaml", yaml.safe_dump(data))
    edit(path, evidence="evidence.yaml")


def test_curated_catalog_and_canonical_parity():
    packages = ext.curated()
    assert set(packages) == {CORE, EXPERIMENTS}
    result = ext.run(BASE, packages[CORE], "baseline")
    ordinary = simulate(BASE, Scenario.from_yaml("scenarios/baseline.yaml"))
    assert result.annual == ordinary.annual
    assert result.cohorts == ordinary.cohorts
    provenance = result.metadata["extension_provenance"]
    assert provenance["equations"] == "canonical_engine"
    receipt = provenance["active_packages"][0]
    assert receipt["classification"] == "canonical"
    assert receipt["scientific_approval"] is False
    assert receipt["manifest"]["authors"]
    assert receipt["manifest"]["license"] == "MIT"
    assert provenance["actual_active_evidence"]["synthetic"]
    assert provenance["base_evidence_sha256"] == provenance["merged_evidence_sha256"]
    assert ordinary.metadata["extension_provenance"]["active_packages"] == []


def test_inspect_register_list_do_not_import_code(package, tmp_path):
    marker = package.parent / "IMPORTED"
    code = (package.parent / "module.py").read_text()
    repin(package, "module.py", f"from pathlib import Path\nPath({str(marker)!r}).touch()\n" + code)
    assert ext.inspect_package(package)["code_executed"] is False
    selected = load(package, tmp_path)
    assert ext.list_packages(tmp_path / "registry.yaml")["code_executed"] is False
    assert not marker.exists()
    result = ext.run(BASE, selected, "reduce_upf_30", "null")
    assert marker.exists()
    baseline = simulate(BASE, Scenario.from_yaml("scenarios/baseline.yaml"))
    assert result.cohorts == baseline.cohorts
    receipt = result.metadata["extension_provenance"]["active_packages"][0]
    assert receipt["classification"] == "third_party"
    assert receipt["selector"] == COMMUNITY
    assert (
        result.metadata["transition_module"]["source_sha256"]
        == receipt["manifest"]["files"]["module.py"]
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"package_id": "demeter.fake"},
        {"classification": "canonical"},
        {"authors": []},
        {"license": " "},
        {"model_versions": ["999.0.0"]},
        {"module_api": "2.0"},
        {"validation_status": "clinically_validated"},
        {"modules": {"bad": {"file": "unlisted.py", "factory": "Factory"}}},
        {"health_structures": ["risk_1"]},
    ],
)
def test_invalid_or_spoofed_metadata_fails(package, changes):
    edit(package, **changes)
    with pytest.raises(ValueError):
        ext.inspect_package(package)


@pytest.mark.parametrize(
    "name", ["../outside.py", "C:/outside.py", "a\\b", "a//b", "a/../b", "NUL.txt"]
)
def test_unsafe_paths_rejected(package, name):
    data = yaml.safe_load(package.read_bytes())
    data["files"][name] = "a" * 64
    write_yaml(package, data)
    with pytest.raises(ValueError, match="Unsafe archive path"):
        ext.inspect_package(package)


def test_symlink_rejected(package, monkeypatch):
    target = package.parent / "module.py"
    original = Path.is_symlink
    monkeypatch.setattr(Path, "is_symlink", lambda self: self == target or original(self))
    with pytest.raises(ValueError, match="symlinks"):
        ext.inspect_package(package)


@pytest.mark.parametrize("name", ["module.py", "scenario.yaml", "package.yaml"])
def test_modified_files_rejected_before_execution(package, tmp_path, name):
    selected = load(package, tmp_path)
    path = package.parent / name
    path.write_bytes(path.read_bytes() + b"\n# changed\n")
    with pytest.raises(ValueError, match="changed|checksum"):
        ext.run(BASE, selected, "reduce_upf_30", "null")
    with pytest.raises(ValueError, match="checksum"):
        ext.resolve(COMMUNITY, tmp_path / "registry.yaml")


def test_registration_is_version_pinned(package, tmp_path):
    load(package, tmp_path)
    edit(package, description="Changed publisher metadata")
    with pytest.raises(ValueError, match="immutable"):
        ext.register(package, tmp_path / "registry.yaml")
    edit(package, version="1.0.1")
    ext.register(package, tmp_path / "registry.yaml")
    assert ext.resolve("community.null@1.0.1", tmp_path / "registry.yaml")


def test_registry_cannot_replace_package_file(package):
    with pytest.raises(ValueError, match="outside pinned"):
        ext.register(package, package)


@pytest.mark.parametrize(
    "kind,key,record",
    [
        ("parameters", "h_to_ir_rate", BASE.parameters["h_to_ir_rate"].model_dump(mode="json")),
        ("parameters", "other.rate", BASE.parameters["h_to_ir_rate"].model_dump(mode="json")),
        ("sources", "arbitrary.source", {}),
        ("datasets", "arbitrary", {}),
    ],
)
def test_overlay_cannot_override_or_escape_namespace(package, tmp_path, kind, key, record):
    overlay(package, {kind: {key: record}})
    selected = load(package, tmp_path)
    with pytest.raises(ValueError, match="override|namespace|only append"):
        selected.evidence_registry(BASE)


def test_namespaced_evidence_appends_and_preserves_base(package, tmp_path):
    original = BASE.model_dump(mode="json")
    parameter = BASE.parameters["h_to_ir_rate"].model_dump(mode="json")
    parameter["key"] = "community.null.rate"
    overlay(
        package,
        {
            "parameters": {parameter["key"]: parameter},
            "scientific_blockers": ["Example unresolved mapping"],
        },
    )
    selected = load(package, tmp_path)
    merged = selected.evidence_registry(BASE)
    assert merged.parameters[parameter["key"]].value == BASE.value("h_to_ir_rate")
    assert merged.scientific_blockers == BASE.scientific_blockers + ["Example unresolved mapping"]
    merged.parameters["h_to_ir_rate"].value = 0
    assert BASE.model_dump(mode="json") == original
    result = ext.run(BASE, selected, "reduce_upf_30", "null")
    provenance = result.metadata["extension_provenance"]
    assert provenance["added_parameter_keys"] == [parameter["key"]]
    assert provenance["base_evidence_sha256"] != provenance["merged_evidence_sha256"]
    assert result.validation_only


def test_existing_source_cannot_be_replaced(package, tmp_path):
    key, source = next(iter(BASE.sources.items()))
    overlay(package, {"sources": {key: source.model_dump(mode="json")}})
    with pytest.raises(ValueError, match="override existing sources"):
        load(package, tmp_path).evidence_registry(BASE)


@pytest.mark.parametrize(
    "changes,expected",
    [
        ({"unresolved": True, "value": None}, "Unresolved|unresolved"),
        ({"model_role": "benchmark_only"}, "Invalid module evidence dependency"),
        ({"uncertainty": None}, "uncertainty"),
    ],
)
def test_incomplete_parameter_cannot_be_used(package, tmp_path, changes, expected):
    parameter = BASE.parameters["h_to_ir_rate"].model_dump(mode="json")
    parameter.update(key="community.null.rate", **changes)
    overlay(package, {"parameters": {parameter["key"]: parameter}})
    code = """from demeter.contracts import ParameterDependency
from demeter.examples.transition_modules import NoDietEffect
class CommunityNull(NoDietEffect):
    def describe(self, interface):
        spec = super().describe(interface)
        return spec.model_copy(update={"parameters": (*spec.parameters, ParameterDependency(key="community.null.rate", unit="hazard_per_year"))})
"""
    repin(package, "module.py", code)
    with pytest.raises(ValueError, match=expected):
        ext.run(BASE, load(package, tmp_path), "reduce_upf_30", "null")


def test_package_cannot_enable_scientific_execution(package):
    repin(package, "scenario.yaml", "name: unauthorized_claim\nmode: scientific\n")
    with pytest.raises(ValueError, match="validation-mode"):
        ext.inspect_package(package)


def test_factory_cannot_misattribute_an_unpinned_class(package, tmp_path):
    repin(
        package,
        "module.py",
        "from demeter.examples.transition_modules import NoDietEffect\ndef CommunityNull():\n    return NoDietEffect()\n",
    )
    with pytest.raises(ValueError, match="defined in its pinned"):
        ext.run(BASE, load(package, tmp_path), "reduce_upf_30", "null")


def test_structural_comparison_retains_both_definitions():
    result = ext.compare(
        BASE, ext.resolve(CORE), "baseline", ext.resolve(EXPERIMENTS), "prechronic_baseline"
    )
    assert result["left"]["metadata"]["health_structure"] == "legacy"
    assert result["right"]["metadata"]["health_structure"] == "risk_1"
    assert set(result["outcomes"]) == {
        "life_expectancy",
        "t2d_free_life_expectancy",
        "cumulative_deaths",
    }
    assert result["validation_only"]
    assert "not causal attribution" in result["interpretation"]
    assert (
        result["left"]["metadata"]["extension_provenance"]["active_packages"][0]["classification"]
        == "canonical"
    )
    assert (
        result["right"]["metadata"]["extension_provenance"]["active_packages"][0]["classification"]
        == "experimental"
    )


def test_null_comparison_matches_canonical_baseline():
    result = ext.compare(
        BASE,
        ext.resolve(CORE),
        "baseline",
        ext.resolve(EXPERIMENTS),
        "reduce_upf_30",
        right_module="null",
    )
    assert all(v["absolute_delta"] == 0 for v in result["outcomes"].values())
    assert result["left"]["cohorts"] == result["right"]["cohorts"]


def test_incompatible_comparison_rejected_before_import(package, tmp_path):
    repin(package, "scenario.yaml", "name: short\nyears: 2\n")
    repin(package, "module.py", "raise RuntimeError('must not import')\n")
    with pytest.raises(ValueError, match="equal horizons"):
        ext.compare(
            BASE,
            ext.resolve(CORE),
            "baseline",
            load(package, tmp_path),
            "reduce_upf_30",
            right_module="null",
        )


def test_legacy_direct_module_remains_explicitly_unregistered():
    result = simulate(BASE, Scenario(name="direct", years=1), transition_module=NoDietEffect())
    metadata = result.metadata["extension_provenance"]
    assert metadata["active_packages"] == []
    assert metadata["equations"] == "unregistered_module"
    assert metadata["unregistered_module"] == result.metadata["transition_module"]


def test_cli_register_run_compare(package, tmp_path):
    runner = CliRunner()
    registry = str(tmp_path / "registry.yaml")
    args = ["--local-registry", registry]
    result = runner.invoke(app, ["extensions", "register", str(package), *args])
    assert result.exit_code == 0, result.exception
    assert json.loads(result.stdout)["code_executed"] is False
    result = runner.invoke(
        app, ["extensions", "run", COMMUNITY, "reduce_upf_30", "--module", "null", *args]
    )
    assert result.exit_code == 0, result.exception
    assert json.loads(result.stdout)["metadata"]["extension_provenance"]["module_entry"] == "null"
    result = runner.invoke(
        app,
        [
            "extensions",
            "compare",
            CORE,
            "baseline",
            COMMUNITY,
            "reduce_upf_30",
            "--right-module",
            "null",
            *args,
        ],
    )
    assert result.exit_code == 0, result.exception
    assert json.loads(result.stdout)["outcomes"]["cumulative_deaths"]["absolute_delta"] == 0
