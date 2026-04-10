import unittest
from pathlib import Path


class ReleaseWorkflowTests(unittest.TestCase):
    def test_release_workflow_declares_expected_triggers_and_steps(self):
        workflow = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "release.yml"

        self.assertTrue(workflow.exists(), "release workflow file should exist")

        text = workflow.read_text(encoding="utf-8")

        self.assertIn("workflow_dispatch:", text)
        self.assertIn("tags:", text)
        self.assertIn("- 'v*'", text)
        self.assertIn("python -m unittest tests.test_installer tests.test_release_workflow tests.test_vpa_cli tests.test_wyckoff_engine_v2 -v", text)
        self.assertIn("python -m installer.build_release --output-dir dist", text)
        self.assertIn("actions/upload-artifact", text)
        self.assertIn("softprops/action-gh-release", text)


if __name__ == "__main__":
    unittest.main()
