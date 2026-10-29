from pathlib import Path
import tempfile
import unittest

from harness.install import install_skills


class IntegrationTests(unittest.TestCase):
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
            self.assertEqual(result["installed"], ["parallel-implementation"])
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
