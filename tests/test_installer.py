import tempfile
import unittest
import zipfile
from pathlib import Path


class InstallerTests(unittest.TestCase):
    def test_resolve_targets_expands_all(self):
        from installer.install import resolve_targets

        self.assertEqual(
            resolve_targets("all"),
            ["codex", "claudecode", "kimi", "openclaw"],
        )

    def test_default_adapter_dirs_only_for_supported_defaults(self):
        from installer.install import default_adapter_dir

        self.assertEqual(
            default_adapter_dir("codex"),
            Path.home() / ".codex" / "skills" / "wyckoff-vpa",
        )
        self.assertEqual(
            default_adapter_dir("claudecode"),
            Path.home() / ".claude" / "skills" / "wyckoff-vpa",
        )
        self.assertIsNone(default_adapter_dir("kimi"))
        self.assertIsNone(default_adapter_dir("openclaw"))

    def test_install_package_writes_runtime_and_target_adapters(self):
        from installer.install import install_package

        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            runtime_root = workspace / "runtime"
            adapters_root = workspace / "adapters"

            install_package(
                source_root=repo_root,
                runtime_root=runtime_root,
                targets=["codex", "kimi"],
                adapters_root=adapters_root,
                create_venv=False,
                install_deps=False,
            )

            self.assertTrue((runtime_root / "bin" / "wyckoff-vpa").exists())
            self.assertTrue((runtime_root / "app" / "vpa.py").exists())
            self.assertTrue((runtime_root / "app" / "SKILL.md").exists())

            codex_adapter = adapters_root / "codex" / "SKILL.md"
            kimi_adapter = adapters_root / "kimi" / "PROMPT.md"

            self.assertTrue(codex_adapter.exists())
            self.assertTrue(kimi_adapter.exists())

            codex_text = codex_adapter.read_text(encoding="utf-8")
            kimi_text = kimi_adapter.read_text(encoding="utf-8")

            self.assertIn(str(runtime_root / "bin" / "wyckoff-vpa"), codex_text)
            self.assertIn("name: wyckoff-vpa", codex_text)
            self.assertIn(str(runtime_root / "bin" / "wyckoff-vpa"), kimi_text)
            self.assertNotIn("python vpa.py", codex_text)
            self.assertNotIn(' resolve "<query>"', codex_text)
            self.assertIn("--deep", codex_text)
            self.assertIn("github.com/tedeyang/wyckoffsoulskill", codex_text)
            self.assertIn("uninstall", codex_text)

    def test_uninstall_package_removes_runtime_and_adapters(self):
        from installer.install import install_package, uninstall_package

        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            runtime_root = workspace / "runtime"
            adapters_root = workspace / "adapters"

            install_package(
                source_root=repo_root,
                runtime_root=runtime_root,
                targets=["codex", "kimi"],
                adapters_root=adapters_root,
                create_venv=False,
                install_deps=False,
            )

            removed = uninstall_package(
                runtime_root=runtime_root,
                targets=["codex", "kimi"],
                adapters_root=adapters_root,
            )

            self.assertFalse(runtime_root.exists())
            self.assertFalse((adapters_root / "codex").exists())
            self.assertFalse((adapters_root / "kimi").exists())
            self.assertIn(runtime_root, removed["paths"])

    def test_build_release_archive_contains_installer_and_runtime_sources(self):
        from installer.build_release import build_release_archive

        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = build_release_archive(repo_root, Path(temp_dir))

            self.assertTrue(archive_path.exists())
            self.assertEqual(archive_path.suffix, ".zip")

            with zipfile.ZipFile(archive_path) as archive:
                names = set(archive.namelist())

            self.assertIn("wyckoff-vpa/SKILL.md", names)
            self.assertIn("wyckoff-vpa/vpa.py", names)
            self.assertIn("wyckoff-vpa/installer/install.py", names)
            self.assertIn("wyckoff-vpa/.github/workflows/release.yml", names)
            self.assertIn("wyckoff-vpa/README.md", names)


if __name__ == "__main__":
    unittest.main()
