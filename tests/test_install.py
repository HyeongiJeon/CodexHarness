from pathlib import Path
import re
import tempfile
import unittest

from harness.install import install_skills


class IntegrationTests(unittest.TestCase):
    def test_selective_install_includes_transitive_skill_links(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            result = install_skills(project, ["completion-verification"])
            target = project / ".agents/skills"
            self.assertTrue((target / "final-delivery-verification/SKILL.md").is_file())
            self.assertTrue((target / "time-budget-management/SKILL.md").is_file())
            self.assertEqual(len(result["installed"]), len(set(result["installed"])))
            for path in target.rglob("*.md"):
                for ref in re.findall(r"\]\(([^)]+)\)", path.read_text()):
                    if "://" not in ref and not ref.startswith("#"):
                        self.assertTrue((path.parent / ref.split("#")[0]).exists(), f"{path}: {ref}")
            again = install_skills(project, ["completion-verification"])
            self.assertEqual(again["installed"], [])

    def test_reinstall_repairs_missing_dependencies_without_overwriting_skill(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            existing = project / ".agents/skills/completion-verification"
            existing.mkdir(parents=True)
            original = "Custom instructions\n[handoff](../final-delivery-verification/SKILL.md)\n"
            (existing / "SKILL.md").write_text(original)
            result = install_skills(project, ["completion-verification"])
            self.assertIn("completion-verification", result["preserved_existing"])
            self.assertEqual((existing / "SKILL.md").read_text(), original)
            self.assertTrue((existing.parent / "final-delivery-verification/SKILL.md").is_file())

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
