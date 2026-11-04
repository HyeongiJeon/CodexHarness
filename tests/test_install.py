from pathlib import Path
import os
import re
import tempfile
import unittest

from harness.install import install_skills
from harness.roles import ROOT
from harness.session import MODES


class IntegrationTests(unittest.TestCase):
    def test_selective_install_copies_only_requested_skills(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            result = install_skills(project, ["completion-verification"])
            target = project / ".agents/skills"
            self.assertEqual(sorted(p.name for p in target.iterdir()), ["completion-verification"])
            self.assertEqual(result, {"installed": ["completion-verification"], "preserved_existing": []})
            again = install_skills(project, ["completion-verification"])
            self.assertEqual(again, {"installed": [], "preserved_existing": ["completion-verification"]})

    def test_every_mode_installs_exactly_its_requested_skills(self):
        for mode in ("dev", "optimize", "qa", "preview"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                project = Path(directory)
                names = MODES[mode]["skills"]
                result = install_skills(project, names)
                self.assertEqual(result["installed"], names)
                self.assertEqual(sorted(p.name for p in (project / ".agents/skills").iterdir()), sorted(names))

    def test_installed_skill_links_resolve_within_itself_or_to_the_harness(self):
        for name in sorted(p.name for p in (ROOT / ".agents/skills").iterdir()):
            with self.subTest(skill=name), tempfile.TemporaryDirectory() as directory:
                project = Path(directory)
                install_skills(project, [name])
                installed = project / ".agents/skills" / name
                for path in installed.rglob("*.md"):
                    for ref in re.findall(r"\]\(([^)]+)\)", path.read_text()):
                        if "://" in ref or ref.startswith("#"):
                            continue
                        relative = os.path.normpath(path.parent.relative_to(installed) / ref.split("#")[0])
                        # Own references ship with the skill; a related skill stays readable in the harness.
                        base = ROOT / ".agents/skills" / name if relative.startswith("..") else installed
                        self.assertTrue((base / relative).exists(), f"{path}: {ref}")

    def test_empty_selection_installs_nothing_but_omitted_selection_installs_all(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            self.assertEqual(install_skills(project, [])["installed"], [])
            self.assertEqual(list((project / ".agents/skills").iterdir()), [])
            self.assertEqual(len(install_skills(project)["installed"]), len(list((ROOT / ".agents/skills").glob("*/SKILL.md"))))

    def test_existing_skill_is_preserved_and_its_links_do_not_pull_in_others(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            existing = project / ".agents/skills/completion-verification"
            existing.mkdir(parents=True)
            original = "Custom instructions\n[handoff](../final-delivery-verification/SKILL.md)\n"
            (existing / "SKILL.md").write_text(original)
            result = install_skills(project, ["completion-verification"])
            self.assertEqual(result, {"installed": [], "preserved_existing": ["completion-verification"]})
            self.assertEqual((existing / "SKILL.md").read_text(), original)
            self.assertFalse((existing.parent / "final-delivery-verification").exists())

    def test_original_instructions_and_existing_skills_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            agents = project / "AGENTS.md"
            agents.write_text("Original project rules")
            existing = project / ".agents/skills/requirement-discovery"
            existing.mkdir(parents=True)
            (existing / "SKILL.md").write_text("Original project skill")
            result = install_skills(project, ["requirement-discovery", "parallel-implementation"])
            self.assertEqual(result["preserved_existing"], ["requirement-discovery"])
            self.assertIn("parallel-implementation", result["installed"])
            self.assertEqual(agents.read_text(), "Original project rules")
            self.assertEqual((existing / "SKILL.md").read_text(), "Original project skill")
            self.assertTrue((project / ".agents/skills/parallel-implementation/references/coordination.md").is_file())

    def test_symlink_to_external_skill_tree_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            external = Path(directory) / "external"
            project.mkdir()
            external.mkdir()
            (project / ".agents").symlink_to(external, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "outside"):
                install_skills(project, ["requirement-discovery"])
            self.assertEqual(list(external.iterdir()), [])
