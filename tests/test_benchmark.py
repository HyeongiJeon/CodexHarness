"""Evidence integrity: agent prose cannot satisfy orchestration verification."""
import json
from pathlib import Path
import tempfile
import unittest

from harness.benchmark import extract_events, orchestration_verified


class EvidenceTests(unittest.TestCase):
    def test_self_report_does_not_count_as_spawn_or_parallel_proof(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            path.write_text(json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "Spawned 3 independent parallel workers successfully."}}) + "\n")
            evidence = extract_events(path)
            self.assertEqual(evidence["subagent_count"], 0)
            self.assertFalse(orchestration_verified(evidence, 3))

    def test_completed_spawn_ids_are_deduplicated(self):
        event = {"type": "item.completed", "item": {"type": "collab_tool_call", "tool": "spawn_agent", "receiver_thread_ids": ["child-a"], "agents_states": {}, "status": "completed"}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            path.write_text("not-json\n" + (json.dumps(event) + "\n") * 2)
            self.assertEqual(extract_events(path)["subagent_count"], 1)

    def test_fresh_and_parallel_proof_are_required_in_addition_to_outputs(self):
        proof = {"subagent_count": 2, "spawn_requests": [{"fork_turns": "none"}] * 2,
                 "child_sessions": [{"forked_from_id": None, "parent_marker_present_in_log": False}] * 2,
                 "parallel_observed_in_session_timestamps": True}
        self.assertTrue(orchestration_verified(proof, 2))
        self.assertFalse(orchestration_verified({**proof, "parallel_observed_in_session_timestamps": False}, 2))
        self.assertFalse(orchestration_verified({**proof, "spawn_requests": [{"fork_turns": "all"}] * 2}, 2))
        self.assertFalse(orchestration_verified({**proof, "child_sessions": []}, 2))
        self.assertTrue(orchestration_verified({"subagent_count": 0}, 0))
        self.assertFalse(orchestration_verified({"subagent_count": 1}, 0))
