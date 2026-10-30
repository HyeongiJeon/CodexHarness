from __future__ import annotations

import tempfile
import tomllib
import unittest
from pathlib import Path

from harness.roles import ROOT, ROLES, launch_overrides, render_config
from harness.tasks import validate_plan


def task(task_id: str, paths: list[str], dependencies: list[str] | None = None) -> dict:
    return {
        "id": task_id,
        "role": "core",
        "objective": "Implement a synthetic feature",
        "inputs": ["acceptance contract"],
        "outputs": ["working feature"],
        "acceptance": ["required behavior passes"],
        "paths": paths,
        "depends_on": dependencies or [],
        "verify": "python3 -m unittest discover -s tests -v",
    }


def overrides(arguments: list[str]) -> dict:
    """Parse actual CLI config values as TOML, including quoting and booleans."""
    result = {}
    if len(arguments) % 2:
        raise AssertionError("config arguments must occur in pairs")
    for flag, assignment in zip(arguments[::2], arguments[1::2]):
        if flag != "-c":
            raise AssertionError(f"unexpected flag: {flag}")
        key, value = assignment.split("=", 1)
        result[key] = tomllib.loads("value = " + value)["value"]
    return result


class RoleConfigTests(unittest.TestCase):
    def test_both_reviewer_bundles_require_citation_gate(self) -> None:
        for path in (".codex/agents/reviewer.toml", "configs/inherited/agents/reviewer.toml"):
            with self.subTest(path=path):
                text = tomllib.loads((ROOT / path).read_text())["developer_instructions"]
                self.assertIn("`evidence citations` on every answer citation before approving", text)

    def test_checked_in_inherited_bundle_does_not_force_model_or_effort(self) -> None:
        bundle = ROOT / "configs/inherited"
        config = tomllib.loads((bundle / "config.toml").read_text())
        documents = [config]
        documents.extend(
            tomllib.loads((bundle / config["agents"][name]["config_file"]).read_text())
            for name in ROLES
        )
        for document in documents:
            with self.subTest(role=document.get("name", "main")):
                self.assertNotIn("model", document)
                self.assertNotIn("model_reasoning_effort", document)

    def test_inherited_bundle_preserves_parent_model_and_effort(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / "inherited"
            config = tomllib.loads(render_config(bundle, "inherited").read_text())
            for key in ("model", "model_reasoning_effort"):
                self.assertNotIn(key, config)
            for name in ROLES:
                role = tomllib.loads((bundle / config["agents"][name]["config_file"]).read_text())
                self.assertEqual(role["name"], name)
                self.assertTrue(role["developer_instructions"])
                self.assertNotIn("model", role)
                self.assertNotIn("model_reasoning_effort", role)
            values = overrides(launch_overrides(bundle))
            self.assertNotIn("model", values)
            self.assertNotIn("model_reasoning_effort", values)

    def test_routed_launch_preserves_main_and_role_model_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="harness bundle ") as directory:
            bundle = Path(directory) / "routed"
            config = tomllib.loads(render_config(bundle, "routed").read_text())
            values = overrides(launch_overrides(bundle))
            self.assertEqual(values["model"], config["model"])
            self.assertEqual(values["model_reasoning_effort"], config["model_reasoning_effort"])
            self.assertEqual(values["agents.max_concurrent_threads_per_session"], 4)
            self.assertIs(values["agents.enabled"], True)
            self.assertIs(values["features.browser_use"], False)
            self.assertIs(values["features.computer_use"], False)
            for name, (model, effort, _, _) in ROLES.items():
                role_path = Path(values[f"agents.{name}.config_file"])
                self.assertTrue(role_path.is_absolute())
                role = tomllib.loads(role_path.read_text())
                self.assertEqual(role["name"], name)
                self.assertEqual((role["model"], role["model_reasoning_effort"]), (model, effort))

    def test_existing_bundle_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory)
            marker = bundle / "keep.txt"
            marker.write_text("existing project data")
            with self.assertRaises(FileExistsError):
                render_config(bundle)
            self.assertEqual(marker.read_text(), "existing project data")
            self.assertEqual(list(bundle.iterdir()), [marker])


class TaskContractTests(unittest.TestCase):
    def test_parallel_ownership_uses_normalized_paths(self) -> None:
        for left, right in [
            ("./src", "src/core.py"),
            ("src//core.py", "src/core.py"),
            ("src/./core.py", "./src/core.py"),
            ("src/", "./src"),
        ]:
            with self.subTest(left=left, right=right):
                errors = validate_plan({"tasks": [task("a", [left]), task("b", [right])]})
                self.assertTrue(any("parallel path conflict" in error for error in errors), errors)

    def test_disjoint_sibling_paths_are_parallel_safe(self) -> None:
        self.assertEqual(validate_plan({"tasks": [
            task("core", ["src/core.py"]),
            task("test", ["tests/test_core.py"]),
            task("prefix", ["src/core.py.backup"]),
        ]}), [])

    def test_transitive_dependencies_allow_sequential_path_handoffs(self) -> None:
        self.assertEqual(validate_plan({"tasks": [
            task("implement", ["src"]),
            task("verify", ["tests"], ["implement"]),
            task("repair", ["./src/core.py"], ["verify"]),
        ]}), [])

    def test_shared_predecessor_does_not_serialize_siblings(self) -> None:
        errors = validate_plan({"tasks": [
            task("design", ["docs/plan.md"]),
            task("left", ["src/core.py"], ["design"]),
            task("right", ["src/core.py"], ["design"]),
        ]})
        self.assertTrue(any("parallel path conflict: left / right" in error for error in errors), errors)

    def test_cycles_and_unknown_dependencies_are_rejected(self) -> None:
        for tasks in [
            [task("self", ["src"], ["self"])],
            [task("a", ["src/a"], ["b"]), task("b", ["src/b"], ["c"]), task("c", ["src/c"], ["a"])],
        ]:
            with self.subTest(tasks=tasks):
                self.assertTrue(any("dependency cycle" in error for error in validate_plan({"tasks": tasks})))
        errors = validate_plan({"tasks": [task("a", ["src"], ["missing"])]})
        self.assertIn("a: unknown dependency", errors)

    def test_invalid_owned_paths_are_rejected(self) -> None:
        for path in ("", ".", "../outside", "src/../shared", "/tmp/outside"):
            with self.subTest(path=path):
                errors = validate_plan({"tasks": [task("a", [path])]})
                self.assertTrue(any("invalid owned path" in error for error in errors), errors)

    def test_incomplete_and_duplicate_contracts_are_rejected(self) -> None:
        self.assertEqual(validate_plan({"tasks": []}), ["plan has no tasks"])
        incomplete = task("a", ["src"])
        del incomplete["verify"]
        errors = validate_plan({"tasks": [incomplete]})
        self.assertTrue(any("missing" in error and "verify" in error for error in errors), errors)
        errors = validate_plan({"tasks": [task("a", ["src/a"]), task("a", ["src/b"])]})
        self.assertIn("duplicate task IDs", errors)

    def test_malformed_plan_structures_return_errors_instead_of_crashing(self) -> None:
        malformed = [None, [], {"tasks": None}, {"tasks": {}}, {"tasks": [None]}, {"tasks": ["a"]}]
        for key, value in [
            ("id", None), ("id", []), ("id", ""),
            ("paths", None), ("paths", "src"), ("paths", [1]),
            ("depends_on", None), ("depends_on", "a"), ("depends_on", [1]),
        ]:
            candidate = task("a", ["src"])
            candidate[key] = value
            malformed.append({"tasks": [candidate]})
        for plan in malformed:
            with self.subTest(plan=plan):
                errors = validate_plan(plan)
                self.assertIsInstance(errors, list)
                self.assertTrue(errors)
                self.assertTrue(all(isinstance(error, str) for error in errors))


if __name__ == "__main__":
    unittest.main()
