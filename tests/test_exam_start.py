from __future__ import annotations

import re
import unittest

from harness.roles import ROOT, ROLES

NEW_SKILLS = ("web-runtime-debugging", "web-ui-patterns", "web-flow-verification")


class ExamStartContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = (ROOT / "EXAM_START.md").read_text()

    def test_one_sentence_and_start_here_preserved(self) -> None:
        self.assertIn("CodexHarness/EXAM_START.md 읽고 시작해줘.", self.text)
        self.assertIn("사전체험", (ROOT / "START_HERE.md").read_text())

    def test_every_role_and_skill_it_names_exists(self) -> None:
        for role in ("requirements", "explorer", "architect", "frontend", "core", "data", "qa", "reviewer", "synthesizer"):
            self.assertIn(role, ROLES)
            self.assertIn(f"| {role} |", self.text)
        for name in set(re.findall(r"--skill ([a-z-]+)", self.text)) | set(NEW_SKILLS):
            self.assertTrue((ROOT / ".agents/skills" / name / "SKILL.md").is_file(), name)

    def test_exam_limits_and_honesty_clauses_present(self) -> None:
        for phrase in ("Git push 금지", "Computer Use 자동화 금지", "Astra 금지", "소급 적용", "web-probe", "확인되지 않은 Cofa"):
            self.assertIn(phrase, self.text)

    def test_every_launch_and_harness_command_parses(self) -> None:
        import subprocess, sys
        for sub in ("doctor", "validate", "web-probe", "install-skills", "launch", "role"):
            self.assertIn(f"harness {sub}", self.text)
        out = subprocess.run([sys.executable, "-m", "harness", "web-probe", "--help"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(out.returncode, 0)

    def test_collaboration_gate_in_runbook_and_lead_role(self) -> None:
        for phrase in ("자동으로 하지 않음: 실제 과제 구현", "사용자가 구현 범위를 승인하기 전에는", "다음 단계 논의"):
            self.assertIn(phrase, self.text)
        self.assertNotIn("현재 과제를 진행해줘", self.text)
        import tomllib
        for path in (".codex/agents/lead.toml", "configs/inherited/agents/lead.toml"):
            instructions = tomllib.loads((ROOT / path).read_text())["developer_instructions"]
            self.assertIn("only after the user approves that scope", instructions)

    def test_new_skills_documented_and_exam_notes_template_linked(self) -> None:
        skills_doc = (ROOT / "docs/skills.md").read_text()
        for name in NEW_SKILLS:
            self.assertIn(f".agents/skills/{name}/SKILL.md", skills_doc)
        self.assertTrue((ROOT / "templates/exam-notes.md").is_file())
        recording = (ROOT / ".agents/skills/decision-and-evidence-recording/SKILL.md").read_text()
        self.assertIn("exam-notes.md", recording)

    def test_web_runtime_skill_names_each_fault_layer(self) -> None:
        body = (ROOT / ".agents/skills/web-runtime-debugging/SKILL.md").read_text()
        for phrase in ("server fault", "frontend fault", "preview-connection fault", "0.0.0.0"):
            self.assertIn(phrase, body)


if __name__ == "__main__":
    unittest.main()
